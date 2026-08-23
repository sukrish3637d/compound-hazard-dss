"""Fetch Copernicus GLO-30 DEM from AWS Open Data registry for configured AOIs."""

import logging
import math
from pathlib import Path
from typing import List, Tuple

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.merge import merge

from src.data_layer.config import AOIConfig, RAW_DEM_DIR, STUDY_AREAS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

S3_BUCKET = "copernicus-dem-30m"
S3_REGION = "eu-central-1"


def get_tile_name(lat: int, lon: int) -> str:
    """Generate Copernicus GLO-30 tile name for a given 1x1 degree lower-left corner."""
    lat_str = f"N{lat:02d}" if lat >= 0 else f"S{abs(lat):02d}"
    lon_str = f"E{lon:03d}" if lon >= 0 else f"W{abs(lon):03d}"
    return f"Copernicus_DSM_COG_10_{lat_str}_00_{lon_str}_00_DEM"


def get_tile_urls(aoi: AOIConfig) -> List[str]:
    """Get list of HTTPS/S3 COG URLs covering the AOI bounding box."""
    min_lat_tile = math.floor(aoi.min_lat)
    max_lat_tile = math.floor(aoi.max_lat) if aoi.max_lat % 1 != 0 else int(aoi.max_lat) - 1
    min_lon_tile = math.floor(aoi.min_lon)
    max_lon_tile = math.floor(aoi.max_lon) if aoi.max_lon % 1 != 0 else int(aoi.max_lon) - 1

    urls = []
    for lat in range(min_lat_tile, max_lat_tile + 1):
        for lon in range(min_lon_tile, max_lon_tile + 1):
            tile_name = get_tile_name(lat, lon)
            # Public HTTPS access on AWS Open Data
            url = f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{tile_name}/{tile_name}.tif"
            urls.append(url)
    return urls


def log_raster_sanity_info(file_path: Path) -> None:
    """Log sanity info: CRS, resolution, bounding box, and nodata gap statistics."""
    with rasterio.open(file_path) as src:
        crs = src.crs
        res = src.res
        bounds = src.bounds
        nodata = src.nodata
        data = src.read(1)

        total_pixels = data.size
        if nodata is not None:
            nodata_count = int(np.sum(data == nodata))
            valid_mask = data != nodata
        else:
            nodata_count = int(np.sum(np.isnan(data)))
            valid_mask = ~np.isnan(data)

        valid_data = data[valid_mask] if np.any(valid_mask) else np.array([])
        min_elev = float(np.min(valid_data)) if valid_data.size > 0 else float("nan")
        max_elev = float(np.max(valid_data)) if valid_data.size > 0 else float("nan")

        logger.info(f"--- DEM Sanity Check: {file_path.name} ---")
        logger.info(f"CRS: {crs}")
        logger.info(f"Resolution (pixel size): {res}")
        logger.info(f"Bounding Box: (left={bounds.left:.4f}, bottom={bounds.bottom:.4f}, right={bounds.right:.4f}, top={bounds.top:.4f})")
        logger.info(f"Dimensions: {src.width} x {src.height} pixels (total: {total_pixels})")
        logger.info(f"No-Data Value: {nodata}")
        logger.info(f"No-Data Gaps: {nodata_count} pixels ({nodata_count / total_pixels * 100:.2f}%)")
        logger.info(f"Elevation Range: [{min_elev:.2f}m, {max_elev:.2f}m]")
        logger.info("-------------------------------------------")


def fetch_aoi_dem(aoi: AOIConfig, output_dir: Path = RAW_DEM_DIR) -> Path:
    """Fetch, merge (if multi-tile), and crop Copernicus GLO-30 DEM for an AOI."""
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{aoi.name}_glo30.tif"

    tile_urls = get_tile_urls(aoi)
    logger.info(f"Fetching DEM for AOI '{aoi.name}' from {len(tile_urls)} tile(s): {tile_urls}")

    # Set rasterio environment for optimized vsicurl / HTTP access
    env_kwargs = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    }

    with rasterio.Env(**env_kwargs):
        src_files = [rasterio.open(url) for url in tile_urls]
        try:
            # Merge and crop directly to the AOI bounding box
            # bounds order in rasterio.merge: (minx, miny, maxx, maxy) -> (min_lon, min_lat, max_lon, max_lat)
            merged_data, out_transform = merge(
                src_files,
                bounds=aoi.bbox,
                nodata=src_files[0].nodata if src_files[0].nodata is not None else -9999.0,
            )

            out_meta = src_files[0].meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": merged_data.shape[1],
                "width": merged_data.shape[2],
                "transform": out_transform,
                "crs": src_files[0].crs or CRS.from_epsg(4326),
                "nodata": src_files[0].nodata if src_files[0].nodata is not None else -9999.0,
                "compress": "lzw",
            })

            with rasterio.open(out_path, "w", **out_meta) as dest:
                dest.write(merged_data)

            logger.info(f"Successfully saved raw DEM to {out_path}")
        finally:
            for src in src_files:
                src.close()

    log_raster_sanity_info(out_path)
    return out_path


def main() -> None:
    """Fetch DEMs for all configured study areas."""
    for name, aoi in STUDY_AREAS.items():
        logger.info(f"Starting DEM acquisition for {name}...")
        fetch_aoi_dem(aoi)


if __name__ == "__main__":
    main()
