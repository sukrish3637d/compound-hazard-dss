"""Unit tests for OSM capture rate metric calculations."""

import geopandas as gpd
from pathlib import Path
import pytest
from shapely.geometry import LineString

from src.data_layer.osm_capture_metric import compute_osm_capture_rate


def test_synthetic_parallel_lines():
    """Verify capture rate calculation with parallel line geometries.

    Extracted stream: (0, 0) -> (100, 0)
    OSM waterway: (0, 50) -> (100, 50)  [Distance = 50m]

    - Buffer 75m: fully encloses OSM line -> 100.0% capture
    - Buffer 25m: does not reach OSM line -> 0.0% capture
    """
    stream_gdf = gpd.GeoDataFrame(
        [{"id": 1}],
        geometry=[LineString([(0, 0), (100, 0)])],
        crs="EPSG:3857",
    )
    osm_gdf = gpd.GeoDataFrame(
        [{"id": 1}],
        geometry=[LineString([(0, 50), (100, 50)])],
        crs="EPSG:3857",
    )

    # Buffer 75m (greater than 50m offset)
    res_75 = compute_osm_capture_rate(osm_gdf, stream_gdf, buffer_meters=75.0)
    assert res_75["capture_rate_percent"] == 100.0
    assert res_75["osm_length_km"] == 0.1  # 100m = 0.1km
    assert res_75["captured_length_km"] == 0.1

    # Buffer 25m (less than 50m offset)
    res_25 = compute_osm_capture_rate(osm_gdf, stream_gdf, buffer_meters=25.0)
    assert res_25["capture_rate_percent"] == 0.0
    assert res_25["osm_length_km"] == 0.1
    assert res_25["captured_length_km"] == 0.0


def test_synthetic_perpendicular_line_half_capture():
    """Verify capture rate calculation with perpendicular line geometry.

    Extracted stream: (0, 0) -> (100, 0)
    OSM waterway: (50, -50) -> (50, 50) [Total length = 100m]

    With buffer 25m, the captured portion along x=50 spans y in [-25, 25] (length 50m).
    Expected capture rate = 50.0m / 100.0m = 50.0%.
    """
    stream_gdf = gpd.GeoDataFrame(
        [{"id": 1}],
        geometry=[LineString([(0, 0), (100, 0)])],
        crs="EPSG:3857",
    )
    osm_gdf = gpd.GeoDataFrame(
        [{"id": 1}],
        geometry=[LineString([(50, -50), (50, 50)])],
        crs="EPSG:3857",
    )

    res = compute_osm_capture_rate(osm_gdf, stream_gdf, buffer_meters=25.0)
    assert res["capture_rate_percent"] == 50.0
    assert res["osm_length_km"] == 0.1
    assert res["captured_length_km"] == 0.05


def test_synthetic_multiple_osm_features():
    """Verify capture rate when OSM has multiple features with varying overlap.

    Extracted stream: (0, 0) -> (100, 0)
    OSM feature 1: (0, 0) -> (100, 0) [100m, 100% captured]
    OSM feature 2: (50, -50) -> (50, 50) [100m, 50m captured with buffer 25m]
    OSM feature 3: (0, 200) -> (100, 200) [100m, 0m captured]

    Total OSM length = 300m (0.3 km)
    Total Captured length = 150m (0.15 km)
    Expected Capture Rate = 150 / 300 = 50.0%
    """
    stream_gdf = gpd.GeoDataFrame(
        [{"id": 1}],
        geometry=[LineString([(0, 0), (100, 0)])],
        crs="EPSG:3857",
    )
    osm_gdf = gpd.GeoDataFrame(
        [{"id": 1}, {"id": 2}, {"id": 3}],
        geometry=[
            LineString([(0, 0), (100, 0)]),
            LineString([(50, -50), (50, 50)]),
            LineString([(0, 200), (100, 200)]),
        ],
        crs="EPSG:3857",
    )

    res = compute_osm_capture_rate(
        osm_gdf, stream_gdf, buffer_meters=25.0, compute_reverse_context=True
    )
    assert res["capture_rate_percent"] == 50.0
    assert res["osm_length_km"] == 0.3
    assert res["captured_length_km"] == 0.15
    assert "reverse_context_only" in res


def test_empty_geometries():
    """Verify graceful handling of empty inputs."""
    stream_gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:3857")
    osm_gdf = gpd.GeoDataFrame(
        [{"id": 1}],
        geometry=[LineString([(0, 0), (100, 0)])],
        crs="EPSG:3857",
    )

    res = compute_osm_capture_rate(osm_gdf, stream_gdf, buffer_meters=75.0)
    assert res["capture_rate_percent"] == 0.0
    assert res["captured_length_km"] == 0.0


_REAL_OSM_DATA_EXISTS = (
    Path("data/raw/osm/wayanad_waterways.geojson").exists()
    and Path("data/processed/dem/streams_sweep/wayanad_threshold_50_vector.geojson").exists()
)


@pytest.mark.skipif(
    not _REAL_OSM_DATA_EXISTS,
    reason="requires local pipeline data -- run fetch_dem/condition_dem/flow_routing/osm_reference first",
)
def test_real_data_integration():
    """Integration test verifying compute_osm_capture_rate executes cleanly on real workspace data.

    Note: This test requires the full local data pipeline to have been run first
    (fetch -> condition -> derive -> route -> sweep -> osm_reference).
    On a fresh clone without local data generated, this test is skipped automatically.
    """
    osm_path = Path("data/raw/osm/wayanad_waterways.geojson")
    stream_path = Path("data/processed/dem/streams_sweep/wayanad_threshold_50_vector.geojson")

    res = compute_osm_capture_rate(osm_path, stream_path, buffer_meters=75.0)
    assert 0.0 <= res["capture_rate_percent"] <= 100.0
    assert res["osm_length_km"] > 0
    assert res["captured_length_km"] > 0
    assert res["buffer_meters"] == 75.0
