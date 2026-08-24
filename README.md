# Compound Hazard Decision Support System (DSS)

A decision support system for compound hazard analysis and risk mitigation (landslides, debris flow runout, river blockage, diversion, and risk assessment).

## Running Tests

To run the test suite:

```bash
pytest tests/data_layer -v
```

### Self-Contained vs. Integration Tests
- **Self-Contained Unit Tests**: The vast majority of tests use synthetic in-memory grids, mock data, and hand-calculated mathematical geometries. These run fast and pass immediately on a fresh repository clone without any external data dependencies.
- **Local Data Pipeline Integration Tests**: A small number of integration tests verify end-to-end processing against real workspace data (which resides in the gitignored `data/` directory). On a fresh clone where local datasets have not yet been generated, these tests are automatically skipped (`SKIPPED`) with an informative message rather than failing:
  - `test_get_final_stream_network_real_data` ([`tests/data_layer/test_drainage_network.py`](file:///d:/projects/compound-hazard-dss/tests/data_layer/test_drainage_network.py))
  - `test_real_data_integration` ([`tests/data_layer/test_osm_capture_metric.py`](file:///d:/projects/compound-hazard-dss/tests/data_layer/test_osm_capture_metric.py))
  - `test_convert_streams_raster_to_vector_real_data` ([`tests/data_layer/test_stream_vectorizer.py`](file:///d:/projects/compound-hazard-dss/tests/data_layer/test_stream_vectorizer.py))

To run these integration tests, generate the local pipeline data first:
```bash
python -m src.data_layer.fetch_dem
python -m src.data_layer.condition_dem
python -m src.data_layer.terrain_derivatives
python -m src.data_layer.flow_routing
python -m src.data_layer.stream_threshold_sweep
python -m src.data_layer.osm_reference
python -m src.data_layer.drainage_network
```
