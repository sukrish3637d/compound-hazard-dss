"""Data layer module for DEM acquisition, conditioning, and terrain derivatives."""

from src.data_layer.config import AOIConfig, STUDY_AREAS, RAW_DEM_DIR, PROCESSED_DEM_DIR
from src.data_layer.fetch_dem import fetch_aoi_dem
from src.data_layer.condition_dem import condition_dem, condition_aoi
from src.data_layer.terrain_derivatives import compute_terrain_derivatives, compute_aoi_derivatives

__all__ = [
    "AOIConfig",
    "STUDY_AREAS",
    "RAW_DEM_DIR",
    "PROCESSED_DEM_DIR",
    "fetch_aoi_dem",
    "condition_dem",
    "condition_aoi",
    "compute_terrain_derivatives",
    "compute_aoi_derivatives",
]
