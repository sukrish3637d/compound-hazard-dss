"""Visualization script: Compare Candidate Stream Networks (25, 50, 100) vs OSM Reference Waterways.

Produces 3-panel comparison figures for Wayanad and Idukki AOIs over terrain hillshade.
"""

import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, List, Tuple

project_root = Path(__file__).resolve().parents[1]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import LightSource
from matplotlib.lines import Line2D
import numpy as np
import rasterio

from src.data_layer.config import (

    AOIConfig,
    PROJECT_ROOT,
    PROCESSED_DEM_DIR,
    RAW_OSM_DIR,
    STUDY_AREAS,
)

NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
STREAMS_SWEEP_DIR = PROCESSED_DEM_DIR / "streams_sweep"
ARTIFACT_DIR = Path(r"C:\Users\sukri\.gemini\antigravity-ide\brain\94f477cb-91ed-479e-bd7d-3eea175b6b06")

CANDIDATE_THRESHOLDS = [25, 50, 100]

# Drainage densities from sweep
DENSITIES = {
    "wayanad": {25: 3.69, 50: 2.64, 100: 1.92},
    "idukki": {25: 4.00, 50: 2.78, 100: 1.95},
}


def load_geojson_lines(geojson_path: Path) -> List[List[Tuple[float, float]]]:
    """Extract line segments from a GeoJSON file."""
    if not geojson_path.exists():
        raise FileNotFoundError(f"GeoJSON file not found: {geojson_path}")

    with open(geojson_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    for feature in data.get("features", []):
        geom = feature.get("geometry", {})
        gtype = geom.get("type")
        coords = geom.get("coordinates", [])
        if gtype == "LineString":
            if len(coords) >= 2:
                lines.append(coords)
        elif gtype == "MultiLineString":
            for part in coords:
                if len(part) >= 2:
                    lines.append(part)

    return lines


def generate_aoi_comparison_figure(aoi: AOIConfig) -> Path:
    """Generate a 3-panel comparison figure for an AOI and save to notebooks/."""
    conditioned_dem_path = PROCESSED_DEM_DIR / f"{aoi.name}_conditioned.tif"
    osm_path = RAW_OSM_DIR / f"{aoi.name}_waterways.geojson"
    output_png = NOTEBOOKS_DIR / f"{aoi.name}_threshold_osm_comparison.png"

    if not conditioned_dem_path.exists():
        raise FileNotFoundError(f"Conditioned DEM not found: {conditioned_dem_path}")
    if not osm_path.exists():
        raise FileNotFoundError(f"OSM reference GeoJSON not found: {osm_path}")

    # 1. Read DEM and compute hillshade
    with rasterio.open(conditioned_dem_path) as src:
        dem_data = src.read(1).astype(float)
        nodata = src.nodata
        bounds = src.bounds
        res = src.res

        if nodata is not None:
            dem_data[dem_data == nodata] = np.nan

        # Kerala approximate resolution in meters
        mid_lat = (bounds.bottom + bounds.top) / 2.0
        dx = res[0] * 111320.0 * np.cos(np.radians(mid_lat))
        dy = res[1] * 110574.0

    ls = LightSource(azdeg=315, altdeg=45)
    dem_filled = np.nan_to_num(dem_data, nan=np.nanmin(dem_data))
    hillshade = ls.hillshade(dem_filled, dx=dx, dy=dy, vert_exag=1.5)
    extent = [bounds.left, bounds.right, bounds.bottom, bounds.top]

    # 2. Load OSM Reference Lines
    osm_lines = load_geojson_lines(osm_path)
    osm_count = len(osm_lines)

    # 3. Create 3-panel figure
    fig, axes = plt.subplots(1, 3, figsize=(24, 8.5), dpi=300, sharey=True)

    stream_color = "#00D4FF"   # Electric Cyan for extracted stream network
    osm_color = "#FF3333"      # Vivid Red/Coral for OSM Reference Waterways

    for idx, t in enumerate(CANDIDATE_THRESHOLDS):
        ax = axes[idx]
        density = DENSITIES.get(aoi.name, {}).get(t, 0.0)

        # Draw Hillshade background
        ax.imshow(hillshade, cmap="gray", extent=extent, origin="upper", alpha=0.9)

        # Load & plot Candidate Extracted Network
        vec_path = STREAMS_SWEEP_DIR / f"{aoi.name}_threshold_{t}_vector.geojson"
        extracted_lines = load_geojson_lines(vec_path)
        extracted_lc = LineCollection(
            extracted_lines,
            colors=stream_color,
            linewidths=1.0,
            alpha=0.85,
            zorder=2,
        )
        ax.add_collection(extracted_lc)

        # Plot OSM Reference lines
        osm_lc = LineCollection(
            osm_lines,
            colors=osm_color,
            linewidths=1.4,
            alpha=0.85,
            zorder=3,
        )
        ax.add_collection(osm_lc)

        # Set bounds & styling
        ax.set_xlim(bounds.left, bounds.right)
        ax.set_ylim(bounds.bottom, bounds.top)
        ax.set_title(
            f"Candidate Threshold = {t} cells\n"
            f"Drainage Density: {density:.2f} km/km² | Segments: {len(extracted_lines):,}",
            fontsize=13,
            fontweight="bold",
            pad=10,
        )
        ax.set_xlabel("Longitude (°E)", fontsize=11)
        if idx == 0:
            ax.set_ylabel("Latitude (°N)", fontsize=11)

        ax.grid(True, linestyle="--", alpha=0.35, color="white")

        # Create panel legend
        legend_elements = [
            Line2D([0], [0], color=stream_color, lw=2.2, label=f"Extracted Streams (T={t})"),
            Line2D([0], [0], color=osm_color, lw=2.2, label=f"OSM Waterways (n={osm_count})"),
        ]
        ax.legend(
            handles=legend_elements,
            loc="upper right",
            frameon=True,
            framealpha=0.88,
            facecolor="#1e1e1e",
            edgecolor="#444444",
            labelcolor="white",
            fontsize=10,
        )

    aoi_title = aoi.name.capitalize()
    fig.suptitle(
        f"{aoi_title} AOI — Extracted Stream Networks (Thresholds 25, 50, 100) vs. OSM Reference Waterways\n"
        f"Bounding Box: Lat [{bounds.bottom:.2f}°N, {bounds.top:.2f}°N], Lon [{bounds.left:.2f}°E, {bounds.right:.2f}°E]",
        fontsize=16,
        fontweight="bold",
        y=0.98,
    )

    plt.tight_layout(rect=[0, 0, 1, 0.92])
    output_png.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_png, dpi=300, bbox_inches="tight")
    plt.close()


    print(f"Generated comparison figure: {output_png}")

    # Copy to artifact dir if present
    if ARTIFACT_DIR.exists():
        dest = ARTIFACT_DIR / output_png.name
        shutil.copyfile(output_png, dest)
        print(f"Copied to artifact directory: {dest}")

    return output_png


def main() -> None:
    """Generate threshold comparison figures for all study areas."""
    for name, aoi in STUDY_AREAS.items():
        print(f"Generating visual comparison for {name}...")
        generate_aoi_comparison_figure(aoi)


if __name__ == "__main__":
    main()
