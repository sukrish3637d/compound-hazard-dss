"""Visualization script for conditioned DEM hillshade and slope map sanity checks."""

from pathlib import Path
import shutil
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource


def create_derivative_visualization(aoi_name: str, title_str: str):
    project_root = Path(__file__).resolve().parents[1]
    dem_path = project_root / "data" / "processed" / "dem" / f"{aoi_name}_conditioned.tif"
    slope_path = project_root / "data" / "processed" / "dem" / f"{aoi_name}_slope.tif"
    output_png = project_root / "notebooks" / f"{aoi_name}_derivatives_sanity_check.png"

    with rasterio.open(dem_path) as src_dem:
        dem_data = src_dem.read(1).astype(float)
        nodata = src_dem.nodata
        bounds = src_dem.bounds

        if nodata is not None:
            dem_data[dem_data == nodata] = np.nan

        dx = src_dem.res[0] * 109500.0
        dy = src_dem.res[1] * 110574.0

    with rasterio.open(slope_path) as src_slope:
        slope_data = src_slope.read(1).astype(float)
        if src_slope.nodata is not None:
            slope_data[slope_data == src_slope.nodata] = np.nan

    # Calculate hillshade from conditioned DEM
    ls = LightSource(azdeg=315, altdeg=45)
    dem_filled = np.nan_to_num(dem_data, nan=np.nanmin(dem_data))
    hillshade = ls.hillshade(dem_filled, dx=dx, dy=dy, vert_exag=1.5)

    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

    fig, axes = plt.subplots(1, 2, figsize=(15, 7), dpi=300)

    # 1. Conditioned Hillshade
    ax1 = axes[0]
    im1 = ax1.imshow(hillshade, cmap="gray", extent=extent, origin="upper")
    ax1.set_title("Conditioned DEM Hillshade (Azimuth 315°, Alt 45°)", fontsize=13, pad=10, fontweight="bold")
    ax1.set_xlabel("Longitude (°E)", fontsize=11)
    ax1.set_ylabel("Latitude (°N)", fontsize=11)
    ax1.grid(True, linestyle=":", alpha=0.3, color="white")

    # 2. Slope Map (in degrees)
    ax2 = axes[1]
    cmap_slope = plt.cm.magma
    im2 = ax2.imshow(slope_data, cmap=cmap_slope, extent=extent, origin="upper", vmin=0, vmax=60)
    ax2.set_title("Slope Gradient (°)", fontsize=13, pad=10, fontweight="bold")
    ax2.set_xlabel("Longitude (°E)", fontsize=11)
    ax2.set_ylabel("Latitude (°N)", fontsize=11)
    ax2.grid(True, linestyle=":", alpha=0.4)

    cbar = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    cbar.set_label("Slope (degrees)", fontsize=11)

    fig.suptitle(
        f"{title_str}\nBounding Box: Lat [{bounds.bottom:.2f}°N, {bounds.top:.2f}°N], Lon [{bounds.left:.2f}°E, {bounds.right:.2f}°E]",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Saved: {output_png}")

    artifact_dir = Path(r"C:\Users\sukri\.gemini\antigravity-ide\brain\d8f931fc-acc6-4c7d-917d-50dc5a9e7ebd")
    if artifact_dir.exists():
        artifact_png = artifact_dir / f"{aoi_name}_derivatives_sanity_check.png"
        shutil.copyfile(output_png, artifact_png)
        print(f"Copied to artifact dir: {artifact_png}")


if __name__ == "__main__":
    create_derivative_visualization("wayanad", "Wayanad AOI Terrain Derivatives Sanity Check")
    create_derivative_visualization("idukki", "Idukki AOI Terrain Derivatives Sanity Check")
