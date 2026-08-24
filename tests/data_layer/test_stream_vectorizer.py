"""Unit tests for stream raster to vector conversion."""

import json
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.data_layer.stream_vectorizer import convert_streams_raster_to_vector


def test_convert_streams_raster_to_vector_synthetic(tmp_path):
    """Verify stream raster to vector conversion with a fully synthetic raster.

    Creates an in-memory 10x10 grid with a straight 4-cell horizontal stream
    at row 5 (cols 2, 3, 4, 5) with D8 flow direction pointer pointing East (1).
    Ensures vectorization produces valid GeoJSON LineString features spanning
    the correct horizontal coordinate range without requiring external data.
    """
    stream_tif = tmp_path / "synthetic_stream.tif"
    flow_dir_tif = tmp_path / "synthetic_flow_dir.tif"
    out_geojson = tmp_path / "synthetic_stream.geojson"

    nrows, ncols = 10, 10
    cell_size = 10.0  # 10m per cell
    stream_arr = np.zeros((nrows, ncols), dtype=np.uint8)
    flow_arr = np.ones((nrows, ncols), dtype=np.uint8)  # 1 = D8 East

    # 4 contiguous stream cells in row 5: columns 2, 3, 4, 5
    stream_arr[5, 2:6] = 1

    transform = from_origin(0.0, 1000.0, cell_size, cell_size)
    crs = "EPSG:32643"

    with rasterio.open(
        stream_tif,
        "w",
        driver="GTiff",
        height=nrows,
        width=ncols,
        count=1,
        dtype=np.uint8,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(stream_arr, 1)

    with rasterio.open(
        flow_dir_tif,
        "w",
        driver="GTiff",
        height=nrows,
        width=ncols,
        count=1,
        dtype=np.uint8,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(flow_arr, 1)

    result_path = convert_streams_raster_to_vector(
        stream_raster_path=stream_tif,
        flow_direction_path=flow_dir_tif,
        output_geojson_path=out_geojson,
    )

    assert result_path.exists()
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 4  # 1 line segment per stream cell link

    all_x = []
    all_y = []
    for feat in data["features"]:
        geom = feat["geometry"]
        assert geom["type"] in ("LineString", "MultiLineString")
        coords = geom["coordinates"]
        assert len(coords) >= 2
        for pt in coords:
            all_x.append(pt[0])
            all_y.append(pt[1])

    # Stream spans cols 2 to 5 -> X coordinates should span [25m, 65m]
    min_x, max_x = min(all_x), max(all_x)
    assert min_x >= 20.0
    assert max_x <= 70.0
    assert max_x - min_x == pytest.approx(40.0, abs=1.0)

    # In Y, the horizontal line should stay tightly localized around row 5 (y ~ 945-955)
    min_y, max_y = min(all_y), max(all_y)
    assert max_y - min_y <= cell_size * 2.0


_REAL_SWEEP_DATA_EXISTS = (
    Path("data/processed/dem/streams_sweep/wayanad_threshold_100.tif").exists()
    and Path("data/processed/dem/wayanad_flow_direction.tif").exists()
)


@pytest.mark.skipif(
    not _REAL_SWEEP_DATA_EXISTS,
    reason="requires local pipeline data -- run fetch_dem/condition_dem/flow_routing/stream_threshold_sweep first",
)
def test_convert_streams_raster_to_vector_real_data(tmp_path):
    """Integration test verifying vectorization on pre-computed workspace data.

    Note: This test requires the full local data pipeline to have been run first
    (fetch -> condition -> derive -> route -> sweep).
    On a fresh clone without local data generated, this test is skipped automatically.
    """
    stream_raster = Path("data/processed/dem/streams_sweep/wayanad_threshold_100.tif")
    flow_dir = Path("data/processed/dem/wayanad_flow_direction.tif")
    out_geojson = tmp_path / "wayanad_test_vec.geojson"

    result_path = convert_streams_raster_to_vector(
        stream_raster_path=stream_raster,
        flow_direction_path=flow_dir,
        output_geojson_path=out_geojson,
    )

    assert result_path.exists()
    with open(result_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) > 0
    first_feat = data["features"][0]
    assert "geometry" in first_feat
    assert first_feat["geometry"]["type"] in ("LineString", "MultiLineString")
    assert len(first_feat["geometry"]["coordinates"]) >= 2
