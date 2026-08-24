"""Canonical drainage network entry point for downstream hazard modeling.

This module exposes the official calibrated stream network (raster and vector)
for study areas, standardized at threshold T=50 (calibrated against OSM waterways
and marginal drainage density efficiency).

Downstream modules (blockage, runout, diversion, risk) should import from this
module rather than referencing exploratory threshold sweep artifacts.
"""

import logging
from pathlib import Path
import shutil
from typing import Dict, Tuple, Union

from src.data_layer.config import (
    AOIConfig,
    PROCESSED_DEM_DIR,
    STUDY_AREAS,
)
from src.data_layer.stream_threshold_sweep import extract_streams_at_threshold
from src.data_layer.stream_vectorizer import convert_streams_raster_to_vector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Calibrated accumulation threshold chosen from OSM capture and marginal efficiency analysis
FINAL_STREAM_THRESHOLD: int = 50


def get_final_stream_paths(aoi: Union[str, AOIConfig]) -> Tuple[Path, Path]:
    """Get the canonical paths for the binary stream raster and vector GeoJSON for an AOI.

    Args:
        aoi: Area of Interest configuration or AOI name string (e.g. 'wayanad', 'idukki').

    Returns:
        Tuple of (binary_stream_raster_path, stream_vector_geojson_path).
    """
    aoi_name = aoi.name if isinstance(aoi, AOIConfig) else str(aoi).strip().lower()
    stream_raster = PROCESSED_DEM_DIR / f"{aoi_name}_streams.tif"
    stream_geojson = PROCESSED_DEM_DIR / f"{aoi_name}_streams.geojson"
    return stream_raster, stream_geojson


def get_final_stream_network(
    aoi: Union[str, AOIConfig],
    threshold: int = FINAL_STREAM_THRESHOLD,
    force_regenerate: bool = False,
) -> Tuple[Path, Path]:
    """Retrieve or generate the canonical stream network raster and vector GeoJSON for an AOI.

    This function serves as the standard documented entry point for downstream hazard
    modules (e.g. culvert blockage, diversion, and runout modeling).

    If the canonical files `{aoi_name}_streams.tif` and `{aoi_name}_streams.geojson`
    already exist in `data/processed/dem/`, their paths are returned immediately.
    If missing (or `force_regenerate=True`), the function will copy from existing
    calibrated sweep artifacts if available, or generate them directly from flow
    accumulation and flow direction grids.

    Args:
        aoi: Area of Interest configuration or AOI name string.
        threshold: Flow accumulation threshold in cell count (default 50).
        force_regenerate: If True, forces re-creation of canonical files.

    Returns:
        Tuple of (stream_raster_path, stream_geojson_path).

    Raises:
        FileNotFoundError: If required flow direction or accumulation input rasters are missing.
    """
    aoi_name = aoi.name if isinstance(aoi, AOIConfig) else str(aoi).strip().lower()
    aoi_config = STUDY_AREAS.get(aoi_name) if isinstance(aoi, str) else aoi

    stream_raster_path, stream_geojson_path = get_final_stream_paths(aoi_name)

    if (
        stream_raster_path.exists()
        and stream_geojson_path.exists()
        and not force_regenerate
    ):
        logger.debug(f"Using existing canonical stream network for '{aoi_name}'")
        return stream_raster_path, stream_geojson_path

    PROCESSED_DEM_DIR.mkdir(parents=True, exist_ok=True)
    sweep_dir = PROCESSED_DEM_DIR / "streams_sweep"

    candidate_sweep_raster = sweep_dir / f"{aoi_name}_threshold_{threshold}.tif"
    candidate_sweep_vector = sweep_dir / f"{aoi_name}_threshold_{threshold}_vector.geojson"

    # Option A: Copy from verified sweep artifacts if available
    if (
        candidate_sweep_raster.exists()
        and candidate_sweep_vector.exists()
        and not force_regenerate
    ):
        logger.info(
            f"Publishing canonical stream network for '{aoi_name}' from sweep artifact (T={threshold})..."
        )
        shutil.copy2(candidate_sweep_raster, stream_raster_path)
        shutil.copy2(candidate_sweep_vector, stream_geojson_path)
        return stream_raster_path, stream_geojson_path

    # Option B: Regenerate directly
    logger.info(f"Generating canonical stream network for '{aoi_name}' (T={threshold})...")
    flow_accum_path = PROCESSED_DEM_DIR / f"{aoi_name}_flow_accumulation.tif"
    flow_direction_path = PROCESSED_DEM_DIR / f"{aoi_name}_flow_direction.tif"

    extract_streams_at_threshold(flow_accum_path, threshold, stream_raster_path)
    convert_streams_raster_to_vector(stream_raster_path, flow_direction_path, stream_geojson_path)

    return stream_raster_path, stream_geojson_path


def publish_all_final_stream_networks() -> Dict[str, Tuple[Path, Path]]:
    """Publish canonical stream networks (T=50) for all configured study areas."""
    published = {}
    for name, aoi in STUDY_AREAS.items():
        raster, vec = get_final_stream_network(aoi, threshold=FINAL_STREAM_THRESHOLD)
        published[name] = (raster, vec)
        logger.info(f"Published canonical streams for {name}: {raster.name}, {vec.name}")
    return published


if __name__ == "__main__":
    publish_all_final_stream_networks()
