"""Flow direction and flow accumulation routing using WhiteboxTools.

This module computes D8 flow direction pointers and flow accumulation grids
from hydrologically conditioned DEMs.
"""

import logging
from pathlib import Path
from typing import Tuple

from whitebox import WhiteboxTools

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


def _compute_d8_pointer(
    conditioned_dem_path: Path,
    output_path: Path,
    wbt: WhiteboxTools,
    esri_pntr: bool = False,
) -> Path:
    """Internal implementation for computing D8 flow pointer via WhiteboxTools."""
    dem_resolved = str(conditioned_dem_path.resolve())
    out_resolved = str(output_path.resolve())

    logger.info(f"Computing D8 flow direction pointer: {dem_resolved} -> {out_resolved}")
    status = wbt.d8_pointer(
        dem=dem_resolved,
        output=out_resolved,
        esri_pntr=esri_pntr,
    )
    if status != 0 or not output_path.exists():
        raise RuntimeError(f"WhiteboxTools D8 pointer computation failed for {conditioned_dem_path}")
    return output_path


def compute_flow_direction(
    conditioned_dem_path: Path,
    output_path: Path,
    method: str = "d8",
) -> Path:
    """Compute flow direction from a conditioned DEM.

    Why D8 was chosen for this project:
    In steep, mountainous terrain such as the Western Ghats (Wayanad and Idukki),
    a single dominant downhill gradient is physically clear and dominant for channelized
    debris flow and stream incision. Furthermore, downstream network extraction and
    raster-to-vector stream topology operations require single-path-per-cell connectivity
    (deterministic 1-to-1 routing) rather than multi-directional dispersion algorithms
    (like D-infinity or FD8). This D8 single-path-per-cell output ensures topologically
    sound, unambiguous channel vectors for culvert blockage and diversion modeling.

    The method parameter is cleanly isolated to allow future extensions (such as
    D-infinity for hillslope moisture dispersion) without altering caller interfaces.

    Args:
        conditioned_dem_path: Path to input conditioned DEM GeoTIFF.
        output_path: Path to write flow direction pointer GeoTIFF.
        method: Flow routing algorithm, currently supports 'd8'.

    Returns:
        Path to the generated flow direction raster.

    Raises:
        FileNotFoundError: If input DEM does not exist.
        ValueError: If an unsupported routing method is requested.
        RuntimeError: If WhiteboxTools execution fails.
    """
    if not conditioned_dem_path.exists():
        raise FileNotFoundError(f"Conditioned DEM file not found at: {conditioned_dem_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(True)

    method_normalized = method.strip().lower()
    if method_normalized == "d8":
        return _compute_d8_pointer(conditioned_dem_path, output_path, wbt)
    elif method_normalized in ("dinf", "d_infinity", "d-infinity"):
        raise NotImplementedError(
            "D-infinity flow routing is not currently supported for channel network extraction. "
            "D8 is required for single-path vectorization."
        )
    else:
        raise ValueError(
            f"Unsupported flow routing method '{method}'. Supported methods: ['d8']"
        )


def compute_flow_accumulation(
    flow_direction_path: Path,
    output_path: Path,
    out_type: str = "cells",
    log: bool = False,
) -> Path:
    """Compute flow accumulation from a D8 flow direction pointer raster.

    Args:
        flow_direction_path: Path to input D8 pointer GeoTIFF.
        output_path: Path to write flow accumulation GeoTIFF.
        out_type: Output type; one of 'cells' (default), 'catchment area', or 'specific contributing area'.
        log: Whether to log-transform the output raster.

    Returns:
        Path to the generated flow accumulation raster.

    Raises:
        FileNotFoundError: If input flow direction raster does not exist.
        RuntimeError: If WhiteboxTools execution fails.
    """
    if not flow_direction_path.exists():
        raise FileNotFoundError(f"Flow direction file not found at: {flow_direction_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(True)

    pntr_resolved = str(flow_direction_path.resolve())
    out_resolved = str(output_path.resolve())

    logger.info(f"Computing D8 flow accumulation: {pntr_resolved} -> {out_resolved} (out_type={out_type})")
    status = wbt.d8_flow_accumulation(
        i=pntr_resolved,
        output=out_resolved,
        out_type=out_type,
        log=log,
        pntr=True,
    )
    if status != 0 or not output_path.exists():
        raise RuntimeError(f"WhiteboxTools D8 flow accumulation failed for {flow_direction_path}")

    logger.info(f"Successfully generated flow accumulation raster at {output_path}")
    return output_path


def route_aoi_flow(aoi: AOIConfig) -> Tuple[Path, Path]:
    """Compute flow direction and flow accumulation for a specific AOI.

    Args:
        aoi: Area of Interest configuration.

    Returns:
        Tuple of (flow_direction_path, flow_accumulation_path).
    """
    conditioned_dem_path = PROCESSED_DEM_DIR / f"{aoi.name}_conditioned.tif"
    flow_direction_path = PROCESSED_DEM_DIR / f"{aoi.name}_flow_direction.tif"
    flow_accum_path = PROCESSED_DEM_DIR / f"{aoi.name}_flow_accumulation.tif"

    logger.info(f"Starting flow routing pipeline for AOI: {aoi.name}")
    compute_flow_direction(conditioned_dem_path, flow_direction_path, method="d8")
    compute_flow_accumulation(flow_direction_path, flow_accum_path)

    return flow_direction_path, flow_accum_path


def main() -> None:
    """Run flow direction and flow accumulation routing for all study areas."""
    for name, aoi in STUDY_AREAS.items():
        logger.info(f"Processing flow routing for {name}...")
        route_aoi_flow(aoi)


if __name__ == "__main__":
    main()
