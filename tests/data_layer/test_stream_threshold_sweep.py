"""Unit tests for stream threshold extraction and drainage density calculation."""

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from src.data_layer.config import AOIConfig
from src.data_layer.stream_threshold_sweep import (
    calculate_drainage_density,
    compute_aoi_area_km2,
    compute_drainage_density,
    extract_streams_at_threshold,
)


def test_calculate_drainage_density_pure_math():
    """Verify pure math calculation of stream length and drainage density.

    Hand calculation:
    - stream_cells = 100
    - cell_size_m = 30.0 m
    - stream_length_km = (100 * 30.0) / 1000.0 = 3.0 km
    - aoi_area_km2 = 1.5 km²
    - expected_density = 3.0 km / 1.5 km² = 2.0 km/km²
    """
    stream_cells = 100
    cell_size_m = 30.0
    aoi_area_km2 = 1.5

    density = calculate_drainage_density(
        stream_cell_count=stream_cells,
        cell_size_m=cell_size_m,
        aoi_area_km2=aoi_area_km2,
    )
    assert density == pytest.approx(2.0)


def test_calculate_drainage_density_zero_streams():
    """Verify zero stream cells returns 0.0 density."""
    density = calculate_drainage_density(
        stream_cell_count=0,
        cell_size_m=30.0,
        aoi_area_km2=500.0,
    )
    assert density == pytest.approx(0.0)


def test_calculate_drainage_density_invalid_inputs():
    """Verify ValueError is raised for invalid area or dimensions."""
    with pytest.raises(ValueError, match="AOI area must be positive"):
        calculate_drainage_density(10, 30.0, -1.0)

    with pytest.raises(ValueError, match="AOI area must be positive"):
        calculate_drainage_density(10, 30.0, 0.0)

    with pytest.raises(ValueError, match="Cell size must be positive"):
        calculate_drainage_density(10, 0.0, 100.0)

    with pytest.raises(ValueError, match="Stream cell count cannot be negative"):
        calculate_drainage_density(-5, 30.0, 100.0)


def test_compute_drainage_density_synthetic_raster(tmp_path):
    """Test compute_drainage_density using a synthetic mock raster with known stream cells.

    Constructs a 10x10 raster where exactly one column (10 cells) is marked as stream (1),
    and the remaining 90 cells are 0.
    """
    mock_raster_path = tmp_path / "mock_stream.tif"
    grid_shape = (10, 10)
    data = np.zeros(grid_shape, dtype=np.uint8)
    data[:, 2] = 1  # 10 stream cells in column 2

    transform = from_origin(76.0, 11.5, 0.0002777777777777778, 0.0002777777777777778)

    with rasterio.open(
        mock_raster_path,
        "w",
        driver="GTiff",
        height=grid_shape[0],
        width=grid_shape[1],
        count=1,
        dtype=rasterio.uint8,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data, 1)

    mock_aoi = AOIConfig(
        name="synthetic_aoi",
        min_lat=11.40,
        max_lat=11.60,
        min_lon=76.00,
        max_lon=76.20,
    )

    cell_size_m = 30.0
    stream_cell_count = 10
    expected_length_km = (stream_cell_count * cell_size_m) / 1000.0  # 0.30 km
    expected_area_km2 = compute_aoi_area_km2(mock_aoi)
    expected_density = expected_length_km / expected_area_km2

    actual_density = compute_drainage_density(
        stream_raster_path=mock_raster_path,
        aoi=mock_aoi,
        cell_size_m=cell_size_m,
    )

    assert actual_density == pytest.approx(expected_density, rel=1e-6)
    assert actual_density > 0.0


def test_extract_streams_at_threshold_synthetic(tmp_path):
    """Test extract_streams_at_threshold on a synthetic accumulation raster."""
    accum_path = tmp_path / "synthetic_accum.tif"
    out_stream_path = tmp_path / "synthetic_stream.tif"

    # 4x4 array with known accumulation values
    accum_values = np.array(
        [
            [1.0, 5.0, 20.0, 45.0],
            [50.0, 100.0, 150.0, 250.0],
            [10.0, 25.0, 500.0, 1000.0],
            [2.0, 4.0, 8.0, 16.0],
        ],
        dtype=np.float32,
    )

    transform = from_origin(76.0, 11.5, 0.00028, 0.00028)

    with rasterio.open(
        accum_path,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype=rasterio.float32,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(accum_values, 1)

    # Threshold = 50: cells >= 50 should be 1, rest 0
    extract_streams_at_threshold(accum_path, threshold=50, output_path=out_stream_path)

    with rasterio.open(out_stream_path) as src:
        stream_data = src.read(1)

    expected_mask = (accum_values >= 50).astype(np.uint8)
    np.testing.assert_array_equal(stream_data, expected_mask)
    assert np.count_nonzero(stream_data == 1) == 6
