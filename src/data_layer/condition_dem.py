"""Hydrologically condition DEMs by filling depressions using WhiteboxTools."""

import logging
from pathlib import Path
from typing import Optional

from whitebox import WhiteboxTools

from src.data_layer.config import (
    AOIConfig,
    PROCESSED_DEM_DIR,
    RAW_DEM_DIR,
    STUDY_AREAS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def condition_dem(
    raw_dem_path: Path,
    output_path: Path,
    fix_flats: bool = True,
    flat_increment: Optional[float] = None,
) -> Path:
    """Run depression filling on a raw DEM using WhiteboxTools (Wang & Liu algorithm)."""
    if not raw_dem_path.exists():
        raise FileNotFoundError(f"Raw DEM file not found at: {raw_dem_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(True)

    logger.info(f"Conditioning DEM: {raw_dem_path} -> {output_path}")
    status = wbt.fill_depressions_wang_and_liu(
        dem=str(raw_dem_path),
        output=str(output_path),
        fix_flats=fix_flats,
        flat_increment=flat_increment,
    )

    if status != 0:
        # Fallback to standard fill_depressions if wang_and_liu encountered an error
        logger.warning("Wang & Liu depression filling failed, attempting standard fill_depressions...")
        fallback_status = wbt.fill_depressions(
            dem=str(raw_dem_path),
            output=str(output_path),
            fix_flats=fix_flats,
            flat_increment=flat_increment,
        )
        if fallback_status != 0:
            raise RuntimeError(f"WhiteboxTools depression filling failed for {raw_dem_path}")

    logger.info(f"Successfully generated conditioned DEM at {output_path}")
    return output_path


def condition_aoi(aoi: AOIConfig) -> Path:
    """Hydrologically condition DEM for a specific AOI."""
    raw_path = RAW_DEM_DIR / f"{aoi.name}_glo30.tif"
    processed_path = PROCESSED_DEM_DIR / f"{aoi.name}_conditioned.tif"
    return condition_dem(raw_path, processed_path)


def main() -> None:
    """Condition DEMs for all study areas."""
    for name, aoi in STUDY_AREAS.items():
        logger.info(f"Starting DEM hydrological conditioning for {name}...")
        condition_aoi(aoi)


if __name__ == "__main__":
    main()
