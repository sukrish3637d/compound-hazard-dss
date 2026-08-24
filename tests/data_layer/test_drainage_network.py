"""Unit tests for canonical drainage network entry points."""

from pathlib import Path
import pytest

from src.data_layer.config import STUDY_AREAS
from src.data_layer.drainage_network import (
    FINAL_STREAM_THRESHOLD,
    get_final_stream_network,
    get_final_stream_paths,
)


def test_final_stream_threshold_value():
    """Verify calibrated threshold constant is 50."""
    assert FINAL_STREAM_THRESHOLD == 50


def test_get_final_stream_paths():
    """Verify path generation for canonical streams."""
    raster, vec = get_final_stream_paths("wayanad")
    assert raster.name == "wayanad_streams.tif"
    assert vec.name == "wayanad_streams.geojson"


_REAL_DATA_EXISTS = all(
    (Path("data/processed/dem") / f"{name}_streams.tif").exists()
    and (Path("data/processed/dem") / f"{name}_streams.geojson").exists()
    for name in STUDY_AREAS
)


@pytest.mark.skipif(
    not _REAL_DATA_EXISTS,
    reason="requires local pipeline data -- run fetch_dem/condition_dem/terrain_derivatives/flow_routing/drainage_network first",
)
def test_get_final_stream_network_real_data():
    """Integration test verifying get_final_stream_network returns existing valid canonical files.

    Note: This test requires the full local data pipeline to have been run first
    (fetch -> condition -> derive -> route -> sweep -> drainage_network).
    On a fresh clone without local data generated, this test is skipped automatically.
    """
    for name, aoi in STUDY_AREAS.items():
        raster_path, vector_path = get_final_stream_network(aoi)
        assert raster_path.exists(), f"Canonical stream raster missing for {name}"
        assert vector_path.exists(), f"Canonical stream vector missing for {name}"
        assert raster_path.stat().st_size > 0
        assert vector_path.stat().st_size > 0
