"""Configuration for study areas and bounding boxes."""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple


@dataclass(frozen=True)
class AOIConfig:
    name: str
    min_lat: float
    max_lat: float
    min_lon: float
    max_lon: float

    @property
    def bbox(self) -> Tuple[float, float, float, float]:
        """Return (min_lon, min_lat, max_lon, max_lat) bounding box."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    @property
    def bounds_dict(self) -> Dict[str, float]:
        return {
            "min_lat": self.min_lat,
            "max_lat": self.max_lat,
            "min_lon": self.min_lon,
            "max_lon": self.max_lon,
        }


# Base paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DEM_DIR = DATA_DIR / "raw" / "dem"
RAW_OSM_DIR = DATA_DIR / "raw" / "osm"
PROCESSED_DEM_DIR = DATA_DIR / "processed" / "dem"

# Study Areas (AOIs)
STUDY_AREAS: Dict[str, AOIConfig] = {
    "wayanad": AOIConfig(
        name="wayanad",
        min_lat=11.42,
        max_lat=11.62,
        min_lon=76.02,
        max_lon=76.22,
    ),
    "idukki": AOIConfig(
        name="idukki",
        min_lat=10.02,
        max_lat=10.22,
        min_lon=76.92,
        max_lon=77.12,
    ),
}
