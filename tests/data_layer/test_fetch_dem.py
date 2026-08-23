"""Unit tests for DEM tile identification and URL generation."""

import pytest
from src.data_layer.config import AOIConfig, STUDY_AREAS
from src.data_layer.fetch_dem import get_tile_name, get_tile_urls


def test_get_tile_name_positive_lat_lon():
    """Verify tile name formatting for positive latitude and longitude."""
    tile_name = get_tile_name(11, 76)
    expected = "Copernicus_DSM_COG_10_N11_00_E076_00_DEM"
    assert tile_name == expected


def test_get_tile_name_zero_and_negative():
    """Verify tile name formatting for zero or negative coordinates."""
    assert get_tile_name(0, 0) == "Copernicus_DSM_COG_10_N00_00_E000_00_DEM"
    assert get_tile_name(-5, -75) == "Copernicus_DSM_COG_10_S05_00_W075_00_DEM"


def test_get_tile_urls_wayanad_single_tile():
    """Verify Wayanad AOI requires exactly one tile (N11 E076)."""
    wayanad_aoi = STUDY_AREAS["wayanad"]
    urls = get_tile_urls(wayanad_aoi)

    assert len(urls) == 1
    assert "Copernicus_DSM_COG_10_N11_00_E076_00_DEM" in urls[0]
    assert urls[0].startswith("https://copernicus-dem-30m.s3.eu-central-1.amazonaws.com/")


def test_get_tile_urls_idukki_two_tiles():
    """Verify Idukki AOI requires exactly two tiles (N10 E076 and N10 E077)."""
    idukki_aoi = STUDY_AREAS["idukki"]
    urls = get_tile_urls(idukki_aoi)

    assert len(urls) == 2
    assert any("Copernicus_DSM_COG_10_N10_00_E076_00_DEM" in u for u in urls)
    assert any("Copernicus_DSM_COG_10_N10_00_E077_00_DEM" in u for u in urls)


def test_get_tile_urls_integer_boundary_case():
    """Verify that an AOI ending exactly on an integer degree boundary does not fetch an extra tile."""
    # AOI spanning 11.2 to 12.0 N, 76.2 to 77.0 E should strictly stay within N11 E076
    boundary_aoi = AOIConfig(
        name="boundary_test",
        min_lat=11.2,
        max_lat=12.0,
        min_lon=76.2,
        max_lon=77.0,
    )
    urls = get_tile_urls(boundary_aoi)
    assert len(urls) == 1
    assert "Copernicus_DSM_COG_10_N11_00_E076_00_DEM" in urls[0]


def test_get_tile_urls_spanning_boundary_case():
    """Verify that an AOI slightly exceeding an integer boundary fetches adjacent tiles."""
    spanning_aoi = AOIConfig(
        name="spanning_test",
        min_lat=11.2,
        max_lat=12.01,
        min_lon=76.2,
        max_lon=77.01,
    )
    urls = get_tile_urls(spanning_aoi)
    assert len(urls) == 4
    expected_tiles = [
        "Copernicus_DSM_COG_10_N11_00_E076_00_DEM",
        "Copernicus_DSM_COG_10_N11_00_E077_00_DEM",
        "Copernicus_DSM_COG_10_N12_00_E076_00_DEM",
        "Copernicus_DSM_COG_10_N12_00_E077_00_DEM",
    ]
    for tile in expected_tiles:
        assert any(tile in u for u in urls)
