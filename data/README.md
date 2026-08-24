# Data Directory

This folder is gitignored — DEM, rainfall, imagery, and other datasets are not committed to version control.

## Directory Structure

- `raw/`: Unmodified input data downloads.
  - `dem/`: Raw Copernicus GLO-30 DEM GeoTIFFs (`{aoi_name}_glo30.tif`).
  - `osm/`: OpenStreetMap natural waterway vector references (`{aoi_name}_waterways.geojson`).
- `processed/`: Intermediate and conditioned datasets.
  - `dem/`:
    - Hydrologically conditioned DEMs: `{aoi_name}_conditioned.tif`
    - Terrain derivatives: `{aoi_name}_slope.tif`, `{aoi_name}_aspect.tif`, `{aoi_name}_plan_curvature.tif`, `{aoi_name}_profile_curvature.tif`
    - Flow routing grids: `{aoi_name}_flow_direction.tif`, `{aoi_name}_flow_accumulation.tif`
    - Canonical stream networks: `{aoi_name}_streams.tif` (binary raster), `{aoi_name}_streams.geojson` (vector lines)
    - Exploratory threshold sweep artifacts: `streams_sweep/{aoi_name}_threshold_{t}.tif`, `streams_sweep/{aoi_name}_threshold_{t}_vector.geojson` (retained for audit/provenance)

---

## Datasets

### Copernicus GLO-30 Digital Elevation Model (DEM)

- **Source**: European Space Agency (ESA) / Copernicus Programme, distributed via [AWS Open Data Registry](https://registry.opendata.aws/copernicus-dem/) (`copernicus-dem-30m` bucket).
- **Format**: Cloud-Optimized GeoTIFF (COG), 32-bit floating point elevation in meters, WGS 84 (EPSG:4326).
- **Resolution**: 30 meters (1 arc-second).
- **Acquisition / Pipeline Target Date**: August 2026.
- **License**: Free and open access under the [Copernicus DEM License](https://spacedata.copernicus.eu/documents/20123/121286/Copernicus_Data_Policy.pdf) (Open Access for Copernicus Sentinel and Contributing Mission data).

#### Areas of Interest (AOIs)

| AOI Name | Latitude Range | Longitude Range | Bounding Box (min_lon, min_lat, max_lon, max_lat) | S3 Tile(s) |
|---|---|---|---|---|
| **Wayanad** | 11.42° N to 11.62° N | 76.02° E to 76.22° E | (76.02, 11.42, 76.22, 11.62) | `Copernicus_DSM_COG_10_N11_00_E076_00_DEM` |
| **Idukki** | 10.02° N to 10.22° N | 76.92° E to 77.12° E | (76.92, 10.02, 77.12, 10.22) | `Copernicus_DSM_COG_10_N10_00_E076_00_DEM`, `Copernicus_DSM_COG_10_N10_00_E077_00_DEM` |

---

### Calibrated Drainage Network Dataset

- **Canonical Files**:
  - Binary Stream Raster: `data/processed/dem/{aoi_name}_streams.tif`
  - Vector Stream Network: `data/processed/dem/{aoi_name}_streams.geojson`
- **Exploration Archive**: `data/processed/dem/streams_sweep/` (thresholds 25, 50, 100, 250, 500, 1000)

#### 1. Routing Method & D8 Selection Rationale
- **Flow Direction**: D8 pointer algorithm implemented via WhiteboxTools.
- **Flow Accumulation**: D8 single-direction accumulation (cell counts).
- **Why D8 over D-Infinity**:
  - In the steep, rugged topography of the Western Ghats (Wayanad & Idukki), single dominant downhill flow gradients govern channelized debris flow paths and stream incision.
  - Downstream modules (culvert blockage, road-stream intersection diversion, and debris runout) require discrete 1-to-1 downstream segment connectivity. D-infinity introduces multi-directional fractional dispersion, which produces ambiguous vector topologies when converted to line networks. D8 yields unambiguous, topologically consistent channel networks.

#### 2. Threshold Calibration & Evaluation Methodology
- **Threshold Sweep**: Evaluated flow accumulation thresholds across two orders of magnitude ($T \in [25, 50, 100, 250, 500, 1000]$ cells, corresponding to $0.0225\,\text{km}^2$ to $0.90\,\text{km}^2$ contributing area).
- **Quantitative Benchmark**: Evaluated candidate networks against crowd-sourced OpenStreetMap (OSM) natural waterway vectors via a spatial capture-rate metric.
- **One-Directional Metric Design**:
  - The metric computes the fraction of OSM waterway length falling within a spatial buffer (default $75\,\text{m}$, $\approx 2.5$ DEM cells) of our extracted stream network.
  - **Rationale**: In rural, heavily forested mountainous regions, OSM waterway coverage is known to have substantial gaps (unmapped ephemeral headwaters, gullies, and upper-slope channels). A low reverse capture (fraction of extracted network confirmed by OSM) reflects OSM under-mapping rather than extraction error. Treating the reverse as a penalty would unfairly punish fine-scale topographic extraction.
- **Selection of $T = 50$**:
  - **Capture Rate Retention**: $T=50$ captures $80.22\%$ of OSM waterways in Wayanad and $79.94\%$ in Idukki, preserving $\approx 97\%$ of the confirmed channel length captured by the densest candidate ($T=25$).
  - **Marginal Efficiency & Noise Rejection**: Moving from $T=25$ to $T=50$ removes $\sim 28\text{--}30\%$ of total extracted channel length (primarily noisy, unverified hillslope rills) with minimal loss of confirmed channels.
  - **Buffer Sensitivity Stability**: Buffer tolerance sweeps ($50\,\text{m}, 75\,\text{m}, 100\,\text{m}$) confirmed rank stability ($T=25 > T=50 > T=100$) without rank inversions.
  - **Literature Check**: A literature review found no simple, readily-adoptable automated method that outperforms this proxy-validation approach (density sweep + independent-reference capture-rate check) for this specific calibration problem. More sophisticated methods exist in the literature (e.g. channel cross-section analysis / CSA pruning, slope-adaptive thresholds), but these were developed and validated on much higher-resolution data (1-10m LiDAR) than our 30m Copernicus DEM, and were not demonstrated as directly applicable here without further research. This method is a defensible, documented proxy choice given available data and time constraints -- not a claim that it is optimal or state-of-the-art.

#### 3. Known Limitations & Caveats
- **Proxy Validation**: OSM waterway alignment is a secondary crowd-sourced proxy, not a field-surveyed geodetic benchmark.
- **OSM Rural Coverage Gaps**: Headwater channels (< 1st order) are systematically under-represented in OSM for these districts.
- **Constant Area Threshold Simplification**: A uniform threshold ($T=50$) assumes constant channel initiation criteria across the basin. In reality, channel initiation follows a slope-dependent threshold ($A \cdot S^k \ge C$). Implementing a slope-area-adaptive channel initiation threshold is noted as a recommended future enhancement for subsequent iterations.

---

## Known Data Quirks

### Aspect sentinel value (flat cells)
WhiteboxTools assigns `-1.0°` to flat cells (where slope is 0 and aspect is mathematically undefined) -- 0.66% of cells in Wayanad, 0.24% in Idukki, per verification during pipeline development. This is **not** a valid direction and must not be used as a raw numeric feature in any downstream model.

**Recommended handling (for Module 1 feature engineering -- not yet implemented in this branch):** encode aspect as `(sin(aspect), cos(aspect))` rather than raw degrees, to correctly represent its circular nature (359 degrees and 1 degree are nearly the same direction, which raw degrees don't capture). For flat cells, output an explicit `is_flat` boolean column alongside the sin/cos pair, rather than relying on callers to detect `(0, 0)` themselves -- flat cells should be given `aspect_sin=0, aspect_cos=0, is_flat=True`.

Validation note: any real direction satisfies `sin^2 + cos^2 = 1`, so this magnitude check is a useful invariant for testing the encoding correctness, but `is_flat` -- not magnitude -- should be what downstream code actually branches on when deciding how to treat a cell.
