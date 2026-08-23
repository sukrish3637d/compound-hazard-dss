"""One-off visualization script for Wayanad DEM sanity check."""

import os
from pathlib import Path
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource


def create_visualization():
    project_root = Path(__file__).resolve().parents[1]
    dem_path = project_root / "data" / "raw" / "dem" / "wayanad_glo30.tif"
    output_png = project_root / "notebooks" / "wayanad_dem_sanity_check.png"

    if not dem_path.exists():
        raise FileNotFoundError(f"DEM file not found: {dem_path}")

    with rasterio.open(dem_path) as src:
        dem_data = src.read(1).astype(float)
        nodata = src.nodata
        bounds = src.bounds

        if nodata is not None:
            dem_data[dem_data == nodata] = np.nan

        # Calculate approximate cell size in meters for Kerala latitude (~11.5 N)
        # 1 deg lat ~ 110,574 m; 1 deg lon ~ 111,320 * cos(11.5 deg) ~ 109,085 m
        dx = src.res[0] * 109085.0
        dy = src.res[1] * 110574.0

    # Compute hillshade using Matplotlib's LightSource (azimuth=315, altitude=45)
    ls = LightSource(azdeg=315, altdeg=45)
    # Fill nan for hillshade calculation if any
    dem_filled = np.nan_to_num(dem_data, nan=np.nanmin(dem_data))
    hillshade = ls.hillshade(dem_filled, dx=dx, dy=dy, vert_exag=1.5)

    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

    fig, axes = plt.subplots(1, 2, figsize=(15, 7), dpi=300)

    # 1. Hillshade Plot
    ax1 = axes[0]
    im1 = ax1.imshow(hillshade, cmap="gray", extent=extent, origin="upper")
    ax1.set_title("Terrain Hillshade (Azimuth 315°, Alt 45°)", fontsize=13, pad=10, fontweight="bold")
    ax1.set_xlabel("Longitude (°E)", fontsize=11)
    ax1.set_ylabel("Latitude (°N)", fontsize=11)
    ax1.grid(True, linestyle="--", alpha=0.3, color="white")

    # 2. Elevation Colormap Plot
    ax2 = axes[1]
    cmap = plt.cm.terrain
    im2 = ax2.imshow(dem_data, cmap=cmap, extent=extent, origin="upper")
    ax2.set_title("Copernicus GLO-30 Elevation (m)", fontsize=13, pad=10, fontweight="bold")
    ax2.set_xlabel("Longitude (°E)", fontsize=11)
    ax2.set_ylabel("Latitude (°N)", fontsize=11)
    ax2.grid(True, linestyle="--", alpha=0.4)

    cbar = fig.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)
    cbar.set_label("Elevation (meters above sea level)", fontsize=11)

    fig.suptitle(
        f"Wayanad AOI DEM Sanity Check\nBounding Box: Lat [{bounds.bottom:.2f}°N, {bounds.top:.2f}°N], Lon [{bounds.left:.2f}°E, {bounds.right:.2f}°E]",
        fontsize=15,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"Sanity check visualization saved to: {output_png}")

    # Also copy to artifact directory for display if available
    artifact_dir = Path(r"C:\Users\sukri\.gemini\antigravity-ide\brain\d8f931fc-acc6-4c7d-917d-50dc5a9e7ebd")
    if artifact_dir.exists():
        artifact_png = artifact_dir / "wayanad_dem_sanity_check.png"
        import shutil
        shutil.copyfile(output_png, artifact_png)
        print(f"Copied to artifact directory: {artifact_png}")


if __name__ == "__main__":
    create_visualization()
