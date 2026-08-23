"""Extract terrain derivatives (slope, aspect, plan curvature, profile curvature) from conditioned DEMs."""

import logging
from pathlib import Path
from typing import Dict

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


def compute_terrain_derivatives(
    conditioned_dem_path: Path,
    output_dir: Path = PROCESSED_DEM_DIR,
    aoi_name: str = "",
) -> Dict[str, Path]:
    """Compute slope, aspect, plan curvature, and profile curvature for a given conditioned DEM."""
    if not conditioned_dem_path.exists():
        raise FileNotFoundError(f"Conditioned DEM file not found at: {conditioned_dem_path}")

    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = f"{aoi_name}_" if aoi_name else ""

    derivative_paths = {
        "slope": output_dir / f"{prefix}slope.tif",
        "aspect": output_dir / f"{prefix}aspect.tif",
        "plan_curvature": output_dir / f"{prefix}plan_curvature.tif",
        "profile_curvature": output_dir / f"{prefix}profile_curvature.tif",
    }

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(True)
    dem_str = str(conditioned_dem_path)

    # 1. Slope (in degrees)
    logger.info(f"Computing Slope -> {derivative_paths['slope']}")
    status_slope = wbt.slope(
        dem=dem_str,
        output=str(derivative_paths["slope"]),
        units="degrees",
    )
    if status_slope != 0:
        raise RuntimeError(f"Failed to compute slope for {conditioned_dem_path}")

    # 2. Aspect (in degrees clockwise from North)
    logger.info(f"Computing Aspect -> {derivative_paths['aspect']}")
    status_aspect = wbt.aspect(
        dem=dem_str,
        output=str(derivative_paths["aspect"]),
    )
    if status_aspect != 0:
        raise RuntimeError(f"Failed to compute aspect for {conditioned_dem_path}")

    # 3. Plan Curvature (curvature of the contour line)
    logger.info(f"Computing Plan Curvature -> {derivative_paths['plan_curvature']}")
    status_plan = wbt.plan_curvature(
        dem=dem_str,
        output=str(derivative_paths["plan_curvature"]),
    )
    if status_plan != 0:
        raise RuntimeError(f"Failed to compute plan curvature for {conditioned_dem_path}")

    # 4. Profile Curvature (curvature of the steepest slope)
    logger.info(f"Computing Profile Curvature -> {derivative_paths['profile_curvature']}")
    status_prof = wbt.profile_curvature(
        dem=dem_str,
        output=str(derivative_paths["profile_curvature"]),
    )
    if status_prof != 0:
        raise RuntimeError(f"Failed to compute profile curvature for {conditioned_dem_path}")

    logger.info(f"All terrain derivatives computed successfully for {aoi_name or conditioned_dem_path.name}")
    return derivative_paths


def compute_aoi_derivatives(aoi: AOIConfig) -> Dict[str, Path]:
    """Compute terrain derivatives for a specific AOI."""
    conditioned_dem_path = PROCESSED_DEM_DIR / f"{aoi.name}_conditioned.tif"
    return compute_terrain_derivatives(
        conditioned_dem_path=conditioned_dem_path,
        output_dir=PROCESSED_DEM_DIR,
        aoi_name=aoi.name,
    )


def main() -> None:
    """Compute terrain derivatives for all configured study areas."""
    for name, aoi in STUDY_AREAS.items():
        logger.info(f"Starting terrain derivative calculation for {name}...")
        compute_aoi_derivatives(aoi)


if __name__ == "__main__":
    main()
