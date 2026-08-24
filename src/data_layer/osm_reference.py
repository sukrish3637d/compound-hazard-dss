"""OpenStreetMap waterway reference acquisition module.

This module queries OpenStreetMap via the Overpass API to acquire natural waterway
features (rivers, streams, rapids, waterfalls, brooks) for designated Areas of Interest (AOIs).
Outputs are stored as standardized GeoJSON FeatureCollections for hydrological validation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx

from src.data_layer.config import (
    AOIConfig,
    RAW_OSM_DIR,
    STUDY_AREAS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]

USER_AGENT = "CompoundHazardDSS/1.0 (Hydrological Validation DSS; contact: sukrish3637d@gmail.com)"


def _build_overpass_query(aoi: AOIConfig, natural_only: bool = True) -> str:
    """Build Overpass QL query string for waterways within AOI bounding box."""
    bbox_str = f"{aoi.min_lat},{aoi.min_lon},{aoi.max_lat},{aoi.max_lon}"
    if natural_only:
        filter_str = 'way["waterway"~"^(river|stream|stream_pool|rapids|waterfall|brook)$"]'
    else:
        filter_str = 'way["waterway"]'

    query = f"""[out:json][timeout:60];
(
  {filter_str}({bbox_str});
);
out geom;"""
    return query


def _overpass_to_geojson(overpass_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Overpass JSON elements with geometry into a GeoJSON FeatureCollection."""
    features = []
    for elem in overpass_data.get("elements", []):
        if elem.get("type") == "way" and "geometry" in elem:
            coords = [[pt["lon"], pt["lat"]] for pt in elem["geometry"]]
            if len(coords) < 2:
                continue
            properties = elem.get("tags", {})
            properties["osm_id"] = elem.get("id")
            properties["osm_type"] = elem.get("type")
            
            features.append({
                "type": "Feature",
                "id": elem.get("id"),
                "properties": properties,
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords,
                },
            })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def fetch_osm_waterways(
    aoi: AOIConfig,
    output_path: Optional[Path] = None,
    endpoints: Optional[List[str]] = None,
    timeout: float = 60.0,
) -> Path:
    """Download OpenStreetMap natural waterway data for an AOI bounding box.

    Queries natural waterways (rivers, streams, rapids, waterfalls, brooks)
    from OpenStreetMap via Overpass API and saves as a GeoJSON file.

    Args:
        aoi: Area of Interest configuration with bounding box coordinates.
        output_path: Path to write the output GeoJSON file. Defaults to
            `data/raw/osm/{aoi.name}_waterways.geojson`.
        endpoints: List of Overpass API interpreter URLs to try in sequence.
        timeout: HTTP request timeout in seconds.

    Returns:
        Path to the saved GeoJSON file.

    Raises:
        RuntimeError: If all Overpass API endpoints fail to return data.
    """
    if output_path is None:
        output_path = RAW_OSM_DIR / f"{aoi.name}_waterways.geojson"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    endpoints_to_try = endpoints or OVERPASS_ENDPOINTS
    headers = {"User-Agent": USER_AGENT}

    logger.info(
        f"Querying OSM natural waterways for '{aoi.name}' "
        f"[BBox: Lat {aoi.min_lat}°N-{aoi.max_lat}°N, Lon {aoi.min_lon}°E-{aoi.max_lon}°E]..."
    )

    query = _build_overpass_query(aoi, natural_only=True)
    response_data = None
    last_error = None

    for endpoint in endpoints_to_try:
        try:
            logger.debug(f"Attempting Overpass endpoint: {endpoint}")
            resp = httpx.post(
                endpoint,
                data={"data": query},
                headers=headers,
                timeout=timeout,
            )
            if resp.status_code == 200:
                response_data = resp.json()
                logger.info(f"Successfully received response from {endpoint}")
                break
            else:
                logger.warning(
                    f"Endpoint {endpoint} returned HTTP status {resp.status_code}: {resp.text[:100]}"
                )
        except Exception as err:
            logger.warning(f"Error querying {endpoint}: {err}")
            last_error = err

    if response_data is None:
        raise RuntimeError(
            f"Failed to fetch OSM waterways for AOI '{aoi.name}' from all endpoints. "
            f"Last error: {last_error}"
        )

    geojson_data = _overpass_to_geojson(response_data)
    feature_count = len(geojson_data["features"])

    # Fallback to broader waterway tags if natural waterways yielded 0
    if feature_count == 0:
        logger.warning(
            f"Zero natural waterways found for '{aoi.name}'. Attempting broader 'waterway=*' query..."
        )
        query_fallback = _build_overpass_query(aoi, natural_only=False)
        for endpoint in endpoints_to_try:
            try:
                resp = httpx.post(
                    endpoint,
                    data={"data": query_fallback},
                    headers=headers,
                    timeout=timeout,
                )
                if resp.status_code == 200:
                    response_data = resp.json()
                    geojson_data = _overpass_to_geojson(response_data)
                    feature_count = len(geojson_data["features"])
                    break
            except Exception:
                pass

    logger.info(f"Fetched {feature_count} OSM waterway features for AOI '{aoi.name}'.")

    # Flag suspiciously sparse feature count
    if feature_count < 5:
        logger.warning(
            f"[FLAG] AOI '{aoi.name}' returned only {feature_count} waterway features (< 5). "
            f"Please verify bounding box coordinates ({aoi.bbox}) or regional OSM mapping coverage."
        )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f, indent=2)

    logger.info(f"Saved OSM waterway vector reference to {output_path}")
    return output_path


def main() -> None:
    """Acquire OSM waterway reference vectors for all configured study areas."""
    RAW_OSM_DIR.mkdir(parents=True, exist_ok=True)
    for name, aoi in STUDY_AREAS.items():
        out_path = RAW_OSM_DIR / f"{name}_waterways.geojson"
        logger.info(f"--- Processing OSM reference for {name} ---")
        fetch_osm_waterways(aoi, out_path)


if __name__ == "__main__":
    main()
