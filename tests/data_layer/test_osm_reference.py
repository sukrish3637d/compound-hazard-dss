"""Unit tests for OSM waterway reference acquisition."""

import json
import logging
from unittest.mock import MagicMock, patch
import pytest

from src.data_layer.config import AOIConfig
from src.data_layer.osm_reference import (
    _build_overpass_query,
    _overpass_to_geojson,
    fetch_osm_waterways,
)


@pytest.fixture
def sample_aoi():
    return AOIConfig(
        name="test_aoi",
        min_lat=11.42,
        max_lat=11.62,
        min_lon=76.02,
        max_lon=76.22,
    )


def test_build_overpass_query_natural(sample_aoi):
    """Verify Overpass query string contains correct bbox and waterway filter."""
    query = _build_overpass_query(sample_aoi, natural_only=True)
    assert "11.42,76.02,11.62,76.22" in query
    assert "river|stream" in query
    assert "[out:json]" in query


def test_build_overpass_query_fallback(sample_aoi):
    """Verify fallback query uses broader waterway filter."""
    query = _build_overpass_query(sample_aoi, natural_only=False)
    assert 'way["waterway"]' in query


def test_overpass_to_geojson():
    """Verify parsing Overpass raw elements into GeoJSON FeatureCollection."""
    mock_overpass_response = {
        "elements": [
            {
                "type": "way",
                "id": 101,
                "tags": {"name": "Meenachil River", "waterway": "river"},
                "geometry": [
                    {"lat": 11.50, "lon": 76.05},
                    {"lat": 11.51, "lon": 76.06},
                    {"lat": 11.52, "lon": 76.07},
                ],
            },
            {
                "type": "way",
                "id": 102,
                "tags": {"waterway": "stream"},
                "geometry": [
                    {"lat": 11.55, "lon": 76.10},
                    {"lat": 11.56, "lon": 76.11},
                ],
            },
            {
                "type": "node",  # Should be ignored (not a way)
                "id": 201,
                "lat": 11.50,
                "lon": 76.05,
            },
        ]
    }

    geojson = _overpass_to_geojson(mock_overpass_response)
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) == 2

    feat1 = geojson["features"][0]
    assert feat1["id"] == 101
    assert feat1["properties"]["name"] == "Meenachil River"
    assert feat1["properties"]["waterway"] == "river"
    assert feat1["geometry"]["type"] == "LineString"
    assert feat1["geometry"]["coordinates"] == [
        [76.05, 11.50],
        [76.06, 11.51],
        [76.07, 11.52],
    ]


def test_fetch_osm_waterways_mock(sample_aoi, tmp_path):
    """Verify fetch_osm_waterways saves valid GeoJSON and handles mock response."""
    output_path = tmp_path / "test_waterways.geojson"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"waterway": "stream"},
                "geometry": [
                    {"lat": 11.45, "lon": 76.05},
                    {"lat": 11.46, "lon": 76.06},
                ],
            }
        ]
    }

    with patch("httpx.post", return_value=mock_resp):
        res_path = fetch_osm_waterways(sample_aoi, output_path=output_path)

    assert res_path.exists()
    with open(res_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["type"] == "FeatureCollection"
    assert len(data["features"]) == 1
    assert data["features"][0]["id"] == 1


def test_fetch_osm_waterways_flag_sparse(sample_aoi, tmp_path, caplog):
    """Verify logger flags suspicious sparsity when returned features < 5."""
    output_path = tmp_path / "sparse_waterways.geojson"

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "elements": [
            {
                "type": "way",
                "id": 1,
                "tags": {"waterway": "stream"},
                "geometry": [
                    {"lat": 11.45, "lon": 76.05},
                    {"lat": 11.46, "lon": 76.06},
                ],
            }
        ]
    }

    with caplog.at_level(logging.WARNING):
        with patch("httpx.post", return_value=mock_resp):
            fetch_osm_waterways(sample_aoi, output_path=output_path)

    assert any("[FLAG]" in record.message for record in caplog.records)
