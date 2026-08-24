"""OSM capture rate metric for stream extraction threshold evaluation.

This module provides quantitative validation of DEM-extracted stream networks against
ground-truth / crowd-sourced OpenStreetMap (OSM) waterway networks.

DESIGN NOTE - ONE-DIRECTIONAL CAPTURE METRIC:
This metric evaluates the fraction of OSM waterway length captured within a spatial
buffer of the extracted stream network (OSM -> Extracted).

Why one-directional?
In rural, mountainous, and forested terrains such as Wayanad and Idukki (Western Ghats),
OpenStreetMap waterway coverage is known to have substantial coverage gaps (unmapped
headwater streams, minor tributaries, ephemeral channels).
Consequently:
1. High capture rate of OSM channels indicates our extracted network successfully detects
   validated physical channels.
2. Low reverse capture (what fraction of our extracted network matches OSM) DOES NOT
   indicate erroneous extraction; rather, DEM-based flow accumulation identifies true
   topographic flow paths that were simply never surveyed or mapped in OSM.
Evaluating the reverse direction as a quality penalty would unfairly punish fine-scale,
hydrologically accurate extraction in poorly-mapped rural basins.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import geopandas as gpd
import shapely
from shapely import STRtree

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def _load_geodataframe(
    source: Union[str, Path, gpd.GeoDataFrame, Dict[str, Any]],
) -> gpd.GeoDataFrame:
    """Load spatial data from a file path, GeoJSON dict, or existing GeoDataFrame."""
    if isinstance(source, gpd.GeoDataFrame):
        return source.copy()
    if isinstance(source, dict):
        return gpd.GeoDataFrame.from_features(source.get("features", []))
    path = Path(source)
    if not path.exists():
        raise FileNotFoundError(f"Spatial vector file not found: {path}")
    return gpd.read_file(path)


def compute_osm_capture_rate(
    osm_waterways_path: Union[str, Path, gpd.GeoDataFrame, Dict[str, Any]],
    extracted_streams_path: Union[str, Path, gpd.GeoDataFrame, Dict[str, Any]],
    buffer_meters: float = 75.0,
    target_crs: Optional[Any] = None,
    compute_reverse_context: bool = False,
) -> Dict[str, Any]:
    """Compute the one-directional OSM waterway capture rate of an extracted stream network.

    Loads the OSM waterway lines and extracted stream vector lines, projects both into
    a metric coordinate reference system (UTM), buffers the extracted stream network
    by `buffer_meters`, and calculates what fraction of the total OSM waterway length
    falls within that buffer.

    Design Justification:
        This metric is strictly one-directional (OSM length captured by DEM network).
        In rural and mountainous study areas (e.g. Western Ghats), OSM waterways have
        substantial coverage gaps in headwaters and tributaries. A low reverse confirmation
        (extracted streams covered by OSM) reflects OSM under-mapping rather than DEM
        extraction errors; therefore, reverse coverage is not used as a quality metric.

    Args:
        osm_waterways_path: Path to OSM waterway GeoJSON/Shapefile, GeoDataFrame, or GeoJSON dict.
        extracted_streams_path: Path to extracted stream GeoJSON/Shapefile, GeoDataFrame, or GeoJSON dict.
        buffer_meters: Spatial tolerance buffer distance around extracted stream lines in meters.
            Default is 75m (approx. 2.5 DEM cells at 30m resolution), allowing reasonable tolerance
            for positional disagreement without overly generous dilution.
        target_crs: Optional EPSG code or CRS object in metric units. If None, automatically
            estimates the optimal UTM CRS for geographic datasets.
        compute_reverse_context: If True, computes the reverse overlap as an informational side-stat
            (strictly labeled as context only, not a quality signal).

    Returns:
        Dictionary containing:
            - 'capture_rate_percent': Percentage (0-100) of OSM waterway length inside the stream buffer.
            - 'osm_length_km': Total length of OSM waterway lines in kilometers.
            - 'captured_length_km': Length of OSM waterway lines falling within stream buffer in kilometers.
            - 'buffer_meters': The buffer distance in meters used.
            - 'osm_feature_count': Number of OSM vector features.
            - 'stream_feature_count': Number of extracted stream vector features.
            - 'projected_crs': String representation of CRS used for metric calculations.
            - If compute_reverse_context is True, context-only reverse statistics.
    """
    osm_gdf = _load_geodataframe(osm_waterways_path)
    stream_gdf = _load_geodataframe(extracted_streams_path)

    # Empty geometry checks
    if osm_gdf.empty or stream_gdf.empty:
        total_osm = 0.0
        if not osm_gdf.empty and osm_gdf.crs is not None and not osm_gdf.crs.is_geographic:
            total_osm = shapely.length(osm_gdf.geometry.values).sum() / 1000.0
        return {
            "capture_rate_percent": 0.0,
            "osm_length_km": float(total_osm),
            "captured_length_km": 0.0,
            "buffer_meters": float(buffer_meters),
            "osm_feature_count": len(osm_gdf),
            "stream_feature_count": len(stream_gdf),
            "projected_crs": str(osm_gdf.crs) if osm_gdf.crs else "None",
        }

    # Handle CRS reprojection
    if target_crs is not None:
        osm_proj = osm_gdf.to_crs(target_crs)
        stream_proj = stream_gdf.to_crs(target_crs)
        used_crs = str(target_crs)
    elif osm_gdf.crs is not None and osm_gdf.crs.is_geographic:
        estimated_crs = osm_gdf.estimate_utm_crs()
        osm_proj = osm_gdf.to_crs(estimated_crs)
        stream_proj = stream_gdf.to_crs(estimated_crs)
        used_crs = str(estimated_crs)
    elif stream_gdf.crs is not None and stream_gdf.crs.is_geographic:
        estimated_crs = stream_gdf.estimate_utm_crs()
        osm_proj = osm_gdf.to_crs(estimated_crs) if osm_gdf.crs else osm_gdf
        stream_proj = stream_gdf.to_crs(estimated_crs)
        used_crs = str(estimated_crs)
    else:
        # Already projected or planar coordinates (e.g. synthetic test cases)
        osm_proj = osm_gdf
        stream_proj = stream_gdf
        used_crs = str(osm_gdf.crs) if osm_gdf.crs else "planar"

    # Extract valid geometries
    osm_geoms = osm_proj.geometry.dropna().values
    stream_geoms = stream_proj.geometry.dropna().values

    if len(osm_geoms) == 0:
        return {
            "capture_rate_percent": 0.0,
            "osm_length_km": 0.0,
            "captured_length_km": 0.0,
            "buffer_meters": float(buffer_meters),
            "osm_feature_count": 0,
            "stream_feature_count": len(stream_geoms),
            "projected_crs": used_crs,
        }

    total_osm_len_m = float(shapely.length(osm_geoms).sum())

    if len(stream_geoms) == 0 or total_osm_len_m == 0.0:
        return {
            "capture_rate_percent": 0.0,
            "osm_length_km": total_osm_len_m / 1000.0,
            "captured_length_km": 0.0,
            "buffer_meters": float(buffer_meters),
            "osm_feature_count": len(osm_geoms),
            "stream_feature_count": len(stream_geoms),
            "projected_crs": used_crs,
        }

    # Buffer extracted stream segments
    stream_buffers = shapely.buffer(stream_geoms, distance=buffer_meters)

    # Use spatial index (STRtree) for fast, memory-efficient spatial intersection
    tree = STRtree(stream_buffers)

    captured_len_m = 0.0
    for osm_line in osm_geoms:
        candidate_indices = tree.query(osm_line, predicate="intersects")
        if len(candidate_indices) == 0:
            continue
        candidate_bufs = stream_buffers[candidate_indices]
        merged_buf = shapely.union_all(candidate_bufs)
        inter = shapely.intersection(osm_line, merged_buf)
        captured_len_m += float(shapely.length(inter))

    capture_rate_pct = (captured_len_m / total_osm_len_m) * 100.0 if total_osm_len_m > 0 else 0.0

    result: Dict[str, Any] = {
        "capture_rate_percent": round(capture_rate_pct, 2),
        "osm_length_km": round(total_osm_len_m / 1000.0, 2),
        "captured_length_km": round(captured_len_m / 1000.0, 2),
        "buffer_meters": float(buffer_meters),
        "osm_feature_count": len(osm_geoms),
        "stream_feature_count": len(stream_geoms),
        "projected_crs": used_crs,
    }

    # Optional context-only reverse overlap computation
    if compute_reverse_context:
        total_stream_len_m = float(shapely.length(stream_geoms).sum())
        osm_buffers = shapely.buffer(osm_geoms, distance=buffer_meters)
        osm_tree = STRtree(osm_buffers)
        reverse_captured_m = 0.0
        for stream_line in stream_geoms:
            cand_idx = osm_tree.query(stream_line, predicate="intersects")
            if len(cand_idx) > 0:
                merged_osm_buf = shapely.union_all(osm_buffers[cand_idx])
                inter_stream = shapely.intersection(stream_line, merged_osm_buf)
                reverse_captured_m += float(shapely.length(inter_stream))

        reverse_rate_pct = (
            (reverse_captured_m / total_stream_len_m) * 100.0 if total_stream_len_m > 0 else 0.0
        )
        result["reverse_context_only"] = {
            "note": "Context only, NOT a quality signal due to rural OSM coverage gaps",
            "reverse_extracted_coverage_percent": round(reverse_rate_pct, 2),
            "extracted_total_length_km": round(total_stream_len_m / 1000.0, 2),
            "extracted_captured_length_km": round(reverse_captured_m / 1000.0, 2),
        }

    return result
