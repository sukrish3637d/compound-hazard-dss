import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_layer.osm_capture_metric import compute_osm_capture_rate

aois = ["wayanad", "idukki"]
thresholds = [25, 50, 100]
buffers = [50, 75, 100]

results = []

for aoi in aois:
    osm_path = Path(f"data/raw/osm/{aoi}_waterways.geojson")
    for t in thresholds:
        stream_path = Path(f"data/processed/dem/streams_sweep/{aoi}_threshold_{t}_vector.geojson")
        for b in buffers:
            res = compute_osm_capture_rate(
                osm_path, stream_path, buffer_meters=b, compute_reverse_context=True
            )
            entry = {
                "aoi": aoi,
                "threshold": t,
                "buffer_meters": b,
                "capture_rate_percent": res["capture_rate_percent"],
                "osm_length_km": res["osm_length_km"],
                "captured_length_km": res["captured_length_km"],
                "reverse_extracted_coverage_percent": res["reverse_context_only"]["reverse_extracted_coverage_percent"],
                "extracted_total_length_km": res["reverse_context_only"]["extracted_total_length_km"],
                "extracted_captured_length_km": res["reverse_context_only"]["extracted_captured_length_km"],
            }
            results.append(entry)
            print(
                f"{aoi.capitalize():8s} | T={t:3d} | Buf={b:3d}m | "
                f"Capture={res['capture_rate_percent']:6.2f}% | "
                f"OSM={res['osm_length_km']:6.2f}km | "
                f"Captured={res['captured_length_km']:6.2f}km | "
                f"Extracted_Total={entry['extracted_total_length_km']:7.2f}km | "
                f"Reverse(Context)={entry['reverse_extracted_coverage_percent']:5.2f}%"
            )

with open("data/processed/dem/osm_capture_evaluation.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)

print("\nSaved evaluation results to data/processed/dem/osm_capture_evaluation.json")
