"""Stream raster to vector conversion module.

Converts binary stream rasters to standardized GeoJSON vector lines using WhiteboxTools
RasterStreamsToVector tool and shapefile parsing.
"""

import json
import logging
from pathlib import Path
import struct
import tempfile
from typing import Any, Dict, List, Optional, Tuple

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

CANDIDATE_THRESHOLDS = [25, 50, 100]


def _read_dbf_records(dbf_path: Path) -> List[Dict[str, Any]]:
    """Read attribute records from a DBF file."""
    records = []
    if not dbf_path.exists():
        return records

    with open(dbf_path, "rb") as f:
        header = f.read(32)
        if len(header) < 32:
            return records
        num_records = int.from_bytes(header[4:8], "little")
        header_len = int.from_bytes(header[8:10], "little")
        record_len = int.from_bytes(header[10:12], "little")

        fields: List[Tuple[str, str, int]] = []
        while True:
            field_desc = f.read(32)
            if not field_desc or field_desc[0] == 0x0D or len(field_desc) < 32:
                break
            name = field_desc[:11].replace(b"\x00", b"").decode("ascii", errors="ignore").strip()
            field_type = chr(field_desc[11])
            field_len = field_desc[16]
            fields.append((name, field_type, field_len))

        f.seek(header_len)
        for _ in range(num_records):
            rec_bytes = f.read(record_len)
            if len(rec_bytes) < record_len:
                break
            # First byte is deletion flag (0x20 is valid, 0x2A is deleted)
            if rec_bytes[0] == 0x2A:
                continue
            offset = 1
            row_dict = {}
            for name, field_type, flen in fields:
                val_str = rec_bytes[offset : offset + flen].decode("ascii", errors="ignore").strip()
                offset += flen
                if field_type in ("N", "F"):
                    try:
                        row_dict[name] = float(val_str) if "." in val_str else int(val_str)
                    except ValueError:
                        row_dict[name] = None
                else:
                    row_dict[name] = val_str
            records.append(row_dict)

    return records


def shapefile_to_geojson(shp_path: Path, dbf_path: Optional[Path] = None) -> Dict[str, Any]:
    """Convert an ESRI PolyLine shapefile (and optional DBF) into a GeoJSON FeatureCollection.

    Args:
        shp_path: Path to the .shp file.
        dbf_path: Optional path to the corresponding .dbf file.

    Returns:
        GeoJSON FeatureCollection dict.
    """
    if dbf_path is None:
        candidate_dbf = shp_path.with_suffix(".dbf")
        if candidate_dbf.exists():
            dbf_path = candidate_dbf

    dbf_records = _read_dbf_records(dbf_path) if dbf_path and dbf_path.exists() else []

    features = []
    with open(shp_path, "rb") as f:
        header = f.read(100)
        if len(header) < 100:
            return {"type": "FeatureCollection", "features": []}

        rec_idx = 0
        while True:
            rec_hdr = f.read(8)
            if len(rec_hdr) < 8:
                break
            rec_num, content_len = struct.unpack(">2i", rec_hdr)
            content = f.read(content_len * 2)
            if len(content) < content_len * 2:
                break

            shape_type = struct.unpack("<i", content[:4])[0]
            if shape_type == 3:  # PolyLine
                num_parts, num_points = struct.unpack("<2i", content[36:44])
                parts = list(struct.unpack(f"<{num_parts}i", content[44 : 44 + 4 * num_parts]))
                pts_offset = 44 + 4 * num_parts
                raw_pts = struct.unpack(
                    f"<{num_points * 2}d",
                    content[pts_offset : pts_offset + 16 * num_points],
                )
                points = [(raw_pts[2 * i], raw_pts[2 * i + 1]) for i in range(num_points)]

                parts.append(num_points)
                lines = []
                for p in range(num_parts):
                    segment = points[parts[p] : parts[p + 1]]
                    if len(segment) >= 2:
                        lines.append(segment)

                if lines:
                    geom = (
                        {"type": "MultiLineString", "coordinates": lines}
                        if len(lines) > 1
                        else {"type": "LineString", "coordinates": lines[0]}
                    )
                    props = dbf_records[rec_idx] if rec_idx < len(dbf_records) else {"id": rec_idx}
                    features.append({
                        "type": "Feature",
                        "id": rec_idx,
                        "properties": props,
                        "geometry": geom,
                    })

            rec_idx += 1

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def convert_streams_raster_to_vector(
    stream_raster_path: Path,
    flow_direction_path: Path,
    output_geojson_path: Path,
) -> Path:
    """Convert a binary stream raster to vector GeoJSON using WhiteboxTools.

    Args:
        stream_raster_path: Path to binary stream raster GeoTIFF.
        flow_direction_path: Path to D8 flow direction pointer GeoTIFF.
        output_geojson_path: Path to destination GeoJSON vector file.

    Returns:
        Path to the saved GeoJSON file.
    """
    if not stream_raster_path.exists():
        raise FileNotFoundError(f"Stream raster not found: {stream_raster_path}")
    if not flow_direction_path.exists():
        raise FileNotFoundError(f"Flow direction raster not found: {flow_direction_path}")

    output_geojson_path = Path(output_geojson_path)
    output_geojson_path.parent.mkdir(parents=True, exist_ok=True)

    wbt = WhiteboxTools()
    wbt.set_verbose_mode(False)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_shp = Path(tmp_dir) / "stream_vec.shp"
        status = wbt.raster_streams_to_vector(
            streams=str(stream_raster_path.resolve()),
            d8_pntr=str(flow_direction_path.resolve()),
            output=str(tmp_shp.resolve()),
            esri_pntr=False,
        )
        if status != 0 or not tmp_shp.exists():
            raise RuntimeError(
                f"WhiteboxTools raster_streams_to_vector failed for {stream_raster_path}"
            )

        geojson_data = shapefile_to_geojson(tmp_shp, tmp_shp.with_suffix(".dbf"))

    with open(output_geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_data, f)

    logger.info(
        f"Vectorized {stream_raster_path.name} -> {output_geojson_path.name} "
        f"({len(geojson_data['features'])} line features)"
    )
    return output_geojson_path


def vectorize_aoi_candidate_thresholds(
    aoi: AOIConfig,
    thresholds: Optional[List[int]] = None,
) -> Dict[int, Path]:
    """Vectorize all candidate stream rasters (default 25, 50, 100) for a given AOI."""
    target_thresholds = thresholds or CANDIDATE_THRESHOLDS
    streams_sweep_dir = PROCESSED_DEM_DIR / "streams_sweep"
    flow_dir_path = PROCESSED_DEM_DIR / f"{aoi.name}_flow_direction.tif"

    results = {}
    for t in target_thresholds:
        stream_raster = streams_sweep_dir / f"{aoi.name}_threshold_{t}.tif"
        out_geojson = streams_sweep_dir / f"{aoi.name}_threshold_{t}_vector.geojson"
        logger.info(f"Converting stream raster {stream_raster.name} to vector GeoJSON...")
        convert_streams_raster_to_vector(stream_raster, flow_dir_path, out_geojson)
        results[t] = out_geojson

    return results


def main() -> None:
    """Vectorize candidate thresholds (25, 50, 100) for all study areas."""
    # Clean up any leftover artifacts with .geojson extension from previous raw wbt test
    for shp_junk in (PROCESSED_DEM_DIR / "streams_sweep").glob("*.dbf"):
        shp_junk.unlink(missing_ok=True)
    for shp_junk in (PROCESSED_DEM_DIR / "streams_sweep").glob("*.shx"):
        shp_junk.unlink(missing_ok=True)

    for name, aoi in STUDY_AREAS.items():
        logger.info(f"=== Vectorizing candidate streams for {name} ===")
        vectorize_aoi_candidate_thresholds(aoi)


if __name__ == "__main__":
    main()
