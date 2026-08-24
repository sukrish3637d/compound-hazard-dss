"""Stream threshold sweep and drainage density calculation module.

This module evaluates channel initiation accumulation thresholds across study areas,
generating binary stream networks and reporting drainage density (km/km²).

Note on Drainage Density Target:
Any reference to a ~2-4 km/km² drainage density target is unverified, sourced from
a research synthesis report that was found to contain fabricated citations elsewhere,
and should be treated as a rough guide only, not ground truth -- the real decision
will be made via visual comparison against OpenStreetMap data in a later stage.
"""

import logging
from pathlib import Path
from typing import Dict, List, Sequence, Tuple, Union

import numpy as np
import pandas as pd
import rasterio

from src.data_layer.config import (
    AOIConfig,
    PROCESSED_DEM_DIR,
    STUDY_AREAS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Default threshold sweep values (contributing cells)
DEFAULT_THRESHOLDS: Tuple[int, ...] = (25, 50, 100, 250, 500, 1000)
DEFAULT_CELL_SIZE_M: float = 30.0
STREAMS_SWEEP_DIR: Path = PROCESSED_DEM_DIR / "streams_sweep"


def compute_aoi_area_km2(aoi: AOIConfig) -> float:
    """Calculate approximate bounding box area in km² using spherical earth geometry.

    Args:
        aoi: AOIConfig bounding box specification.

    Returns:
        Area in square kilometers (km²).
    """
    lat_mid = (aoi.min_lat + aoi.max_lat) / 2.0
    lat_km = (aoi.max_lat - aoi.min_lat) * 111.132
    lon_km = (aoi.max_lon - aoi.min_lon) * 111.320 * np.cos(np.radians(lat_mid))
    area_km2 = float(lat_km * lon_km)
    return area_km2


def calculate_drainage_density(
    stream_cell_count: int,
    cell_size_m: float,
    aoi_area_km2: float,
) -> float:
    """Pure mathematical calculation of drainage density.

    Computes total channel length from cell count and nominal cell dimension,
    divided by total catchment / AOI area.

    Args:
        stream_cell_count: Number of stream cells in the grid.
        cell_size_m: Length of one cell side in meters (e.g. 30.0 m).
        aoi_area_km2: Total area of the domain in km².

    Returns:
        Drainage density in km/km².

    Raises:
        ValueError: If aoi_area_km2 <= 0 or cell_size_m <= 0 or stream_cell_count < 0.
    """
    if aoi_area_km2 <= 0:
        raise ValueError(f"AOI area must be positive, got {aoi_area_km2}")
    if cell_size_m <= 0:
        raise ValueError(f"Cell size must be positive, got {cell_size_m}")
    if stream_cell_count < 0:
        raise ValueError(f"Stream cell count cannot be negative, got {stream_cell_count}")

    stream_length_km = (stream_cell_count * cell_size_m) / 1000.0
    density_km_per_km2 = stream_length_km / aoi_area_km2
    return float(density_km_per_km2)


def extract_streams_at_threshold(
    flow_accum_path: Path,
    threshold: Union[int, float],
    output_path: Path,
) -> Path:
    """Threshold a flow accumulation raster to produce a binary stream network raster.

    Cells with accumulation >= threshold are designated as stream cells (value 1),
    while non-stream cells receive value 0.

    Args:
        flow_accum_path: Path to flow accumulation GeoTIFF.
        threshold: Upstream accumulation cell count threshold.
        output_path: Path to write the binary stream GeoTIFF.

    Returns:
        Path to the output binary stream raster.

    Raises:
        FileNotFoundError: If input flow accumulation raster is missing.
    """
    if not flow_accum_path.exists():
        raise FileNotFoundError(f"Flow accumulation file not found at: {flow_accum_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with rasterio.open(flow_accum_path) as src:
        accum_data = src.read(1)
        profile = src.profile.copy()
        nodata_val = src.nodata

        # Create binary stream mask: 1 where accumulation >= threshold, 0 elsewhere
        if nodata_val is not None:
            valid_mask = accum_data != nodata_val
            stream_mask = np.where(valid_mask & (accum_data >= threshold), 1, 0).astype(np.uint8)
        else:
            stream_mask = np.where(accum_data >= threshold, 1, 0).astype(np.uint8)

        profile.update(
            dtype=rasterio.uint8,
            count=1,
            nodata=None,
        )

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(stream_mask, 1)

    logger.debug(f"Extracted stream network at threshold {threshold} -> {output_path}")
    return output_path


def compute_drainage_density(
    stream_raster_path: Path,
    aoi: AOIConfig,
    cell_size_m: float = DEFAULT_CELL_SIZE_M,
) -> float:
    """Calculate drainage density (km/km²) from a binary stream raster and AOI definition.

    Args:
        stream_raster_path: Path to binary stream GeoTIFF (1=stream, 0=non-stream).
        aoi: AOI configuration for area calculation.
        cell_size_m: Linear cell size in meters (nominal 30m for GLO-30 DEM).

    Returns:
        Drainage density in km/km².

    Raises:
        FileNotFoundError: If stream raster file does not exist.
    """
    if not stream_raster_path.exists():
        raise FileNotFoundError(f"Stream raster not found at: {stream_raster_path}")

    with rasterio.open(stream_raster_path) as src:
        stream_data = src.read(1)
        stream_cells = int(np.count_nonzero(stream_data == 1))

    aoi_area_km2 = compute_aoi_area_km2(aoi)
    return calculate_drainage_density(
        stream_cell_count=stream_cells,
        cell_size_m=cell_size_m,
        aoi_area_km2=aoi_area_km2,
    )


def run_threshold_sweep(
    aoi: AOIConfig,
    flow_accum_path: Path,
    thresholds: Sequence[Union[int, float]] = DEFAULT_THRESHOLDS,
    sweep_dir: Path = STREAMS_SWEEP_DIR,
    cell_size_m: float = DEFAULT_CELL_SIZE_M,
) -> pd.DataFrame:
    """Run flow accumulation threshold sweep and compute drainage density for each threshold.

    Intermediate binary stream rasters are saved to:
    data/processed/dem/streams_sweep/{aoi_name}_threshold_{threshold}.tif

    Args:
        aoi: AOIConfig for target study area.
        flow_accum_path: Path to flow accumulation GeoTIFF.
        thresholds: Collection of threshold values to test.
        sweep_dir: Output directory for intermediate threshold rasters.
        cell_size_m: Nominal cell size in meters.

    Returns:
        pandas DataFrame containing columns:
        ['threshold', 'stream_cells', 'stream_length_km', 'drainage_density_km_per_km2'].
    """
    if not flow_accum_path.exists():
        raise FileNotFoundError(f"Flow accumulation file not found at: {flow_accum_path}")

    sweep_dir.mkdir(parents=True, exist_ok=True)
    aoi_area_km2 = compute_aoi_area_km2(aoi)

    results: List[Dict[str, Union[int, float]]] = []

    logger.info(
        f"Starting threshold sweep for {aoi.name} (AOI area: {aoi_area_km2:.2f} km², cell size: {cell_size_m} m)..."
    )

    for thresh in thresholds:
        out_raster = sweep_dir / f"{aoi.name}_threshold_{int(thresh)}.tif"
        extract_streams_at_threshold(flow_accum_path, thresh, out_raster)

        with rasterio.open(out_raster) as src:
            stream_data = src.read(1)
            stream_cells = int(np.count_nonzero(stream_data == 1))

        stream_length_km = (stream_cells * cell_size_m) / 1000.0
        density = calculate_drainage_density(
            stream_cell_count=stream_cells,
            cell_size_m=cell_size_m,
            aoi_area_km2=aoi_area_km2,
        )

        results.append(
            {
                "threshold": int(thresh),
                "stream_cells": stream_cells,
                "stream_length_km": round(stream_length_km, 3),
                "drainage_density_km_per_km2": round(density, 4),
            }
        )

    df = pd.DataFrame(results)
    return df


def sweep_aoi(aoi: AOIConfig) -> Tuple[pd.DataFrame, Path]:
    """Run threshold sweep for a specific AOI and save output CSV.

    Args:
        aoi: AOI configuration.

    Returns:
        Tuple of (results_df, csv_output_path).
    """
    flow_accum_path = PROCESSED_DEM_DIR / f"{aoi.name}_flow_accumulation.tif"
    csv_path = PROCESSED_DEM_DIR / f"{aoi.name}_threshold_sweep.csv"

    df = run_threshold_sweep(aoi, flow_accum_path)
    df.to_csv(csv_path, index=False)
    logger.info(f"Saved threshold sweep table to {csv_path}")

    return df, csv_path


def main() -> None:
    """Run threshold sweep for all configured study areas and display formatted results."""
    for name, aoi in STUDY_AREAS.items():
        logger.info(f"\n=======================================================")
        logger.info(f"  DRAINAGE DENSITY THRESHOLD SWEEP: {name.upper()}")
        logger.info(f"=======================================================")

        df, csv_path = sweep_aoi(aoi)

        print(f"\n--- Threshold Sweep Results: {name.upper()} (Area: {compute_aoi_area_km2(aoi):.2f} km2) ---")
        print(df.to_string(index=False))
        print(f"Results saved to: {csv_path}\n")


if __name__ == "__main__":
    main()
