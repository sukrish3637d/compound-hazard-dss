# Data Directory

This folder is gitignored — DEM, rainfall, imagery, and other datasets are not committed to version control.

## Directory Structure

- `raw/`: Unmodified input data downloads.
  - `dem/`: Raw Copernicus GLO-30 DEM GeoTIFFs (`{aoi_name}_glo30.tif`).
- `processed/`: Intermediate and conditioned datasets.
  - `dem/`: Hydrologically conditioned DEMs (`{aoi_name}_conditioned.tif`) and terrain derivatives (`{aoi_name}_slope.tif`, `{aoi_name}_aspect.tif`, `{aoi_name}_plan_curvature.tif`, `{aoi_name}_profile_curvature.tif`).

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

## Known Data Quirks

### Aspect sentinel value (flat cells)
WhiteboxTools assigns `-1.0°` to flat cells (where slope is 0 and aspect is mathematically undefined) -- 0.66% of cells in Wayanad, 0.24% in Idukki, per verification during pipeline development. This is **not** a valid direction and must not be used as a raw numeric feature in any downstream model.

**Recommended handling (for Module 1 feature engineering -- not yet implemented in this branch):** encode aspect as `(sin(aspect), cos(aspect))` rather than raw degrees, to correctly represent its circular nature (359 degrees and 1 degree are nearly the same direction, which raw degrees don't capture). For flat cells, output an explicit `is_flat` boolean column alongside the sin/cos pair, rather than relying on callers to detect `(0, 0)` themselves -- flat cells should be given `aspect_sin=0, aspect_cos=0, is_flat=True`.

Validation note: any real direction satisfies `sin^2 + cos^2 = 1`, so this magnitude check is a useful invariant for testing the encoding correctness, but `is_flat` -- not magnitude -- should be what downstream code actually branches on when deciding how to treat a cell.
