"""Data layer module for DEM acquisition, conditioning, and terrain derivatives."""

from src.data_layer.config import AOIConfig, STUDY_AREAS, RAW_DEM_DIR, RAW_OSM_DIR, PROCESSED_DEM_DIR
from src.data_layer.fetch_dem import fetch_aoi_dem
from src.data_layer.condition_dem import condition_dem, condition_aoi
from src.data_layer.terrain_derivatives import compute_terrain_derivatives, compute_aoi_derivatives
from src.data_layer.flow_routing import (
    compute_flow_direction,
    compute_flow_accumulation,
    route_aoi_flow,
)
from src.data_layer.stream_threshold_sweep import (
    calculate_drainage_density,
    compute_drainage_density,
    extract_streams_at_threshold,
    run_threshold_sweep,
    sweep_aoi,
)
from src.data_layer.osm_reference import fetch_osm_waterways
from src.data_layer.stream_vectorizer import (
    convert_streams_raster_to_vector,
    vectorize_aoi_candidate_thresholds,
)

from src.data_layer.osm_capture_metric import compute_osm_capture_rate
from src.data_layer.drainage_network import (
    FINAL_STREAM_THRESHOLD,
    get_final_stream_network,
    get_final_stream_paths,
    publish_all_final_stream_networks,
)

__all__ = [
    "AOIConfig",
    "STUDY_AREAS",
    "RAW_DEM_DIR",
    "RAW_OSM_DIR",
    "PROCESSED_DEM_DIR",
    "fetch_aoi_dem",
    "condition_dem",
    "condition_aoi",
    "compute_terrain_derivatives",
    "compute_aoi_derivatives",
    "compute_flow_direction",
    "compute_flow_accumulation",
    "route_aoi_flow",
    "calculate_drainage_density",
    "compute_drainage_density",
    "extract_streams_at_threshold",
    "run_threshold_sweep",
    "sweep_aoi",
    "fetch_osm_waterways",
    "convert_streams_raster_to_vector",
    "vectorize_aoi_candidate_thresholds",
    "compute_osm_capture_rate",
    "FINAL_STREAM_THRESHOLD",
    "get_final_stream_network",
    "get_final_stream_paths",
    "publish_all_final_stream_networks",
]



