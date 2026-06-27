# Crop Oracle

Crop Oracle is a map-first backend for recording weed observations and producing simple weed-pressure predictions. The first pilot workspace is Park Vartopo in Sofia, Bulgaria, with public-area observations treated as rough ecological field notes rather than precise private farm coordinates.

This first version intentionally has no frontend. It provides a FastAPI API, SQLAlchemy models, SQLite local storage, CRUD for fields and weed observations, a rule-based prediction endpoint, seeded map workspace data, and GeoJSON output for observations.

## Local Setup

Use Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Run

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

Interactive docs:

```text
http://127.0.0.1:8000/docs
```

## Test

```bash
pytest
ruff check .
ruff format .
```

## API Examples

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Create a field:

```bash
curl -X POST http://127.0.0.1:8000/fields \
  -H "Content-Type: application/json" \
  -d '{
    "workspace_id": 1,
    "name": "Vartopo observation plot",
    "location_label": "Park Vartopo, Sofia",
    "area_square_meters": 250
  }'
```

Create a weed observation:

```bash
curl -X POST http://127.0.0.1:8000/fields/1/weed-observations \
  -H "Content-Type: application/json" \
  -d '{
    "observed_at": "2026-05-04",
    "species": "Chenopodium album",
    "confidence": 0.8,
    "coverage_percent": 35,
    "density_class": "medium",
    "growth_stage": "seedling",
    "latitude": 42.6581,
    "longitude": 23.2852
  }'
```

Run a rule-based prediction:

```bash
curl -X POST http://127.0.0.1:8000/fields/1/predict \
  -H "Content-Type: application/json" \
  -d '{
    "target_year": 2026,
    "recent_rainfall_mm": 25,
    "recent_mean_temp_c": 20,
    "disturbed_soil": true,
    "crop_established": false
  }'
```

Fetch observation GeoJSON for the default Park Vartopo workspace:

```bash
curl http://127.0.0.1:8000/map/workspaces/1/observations.geojson
```

## Implemented Endpoints

- `GET /health`
- `POST /fields`
- `GET /fields`
- `GET /fields/{field_id}`
- `POST /fields/{field_id}/weed-observations`
- `GET /fields/{field_id}/weed-observations`
- `POST /fields/{field_id}/predict`
- `GET /fields/{field_id}/predictions/latest`
- `POST /map/workspaces`
- `GET /map/workspaces`
- `GET /map/workspaces/{workspace_id}`
- `GET /map/workspaces/{workspace_id}/observations.geojson`

## Map And GeoJSON Notes

The app seeds one default map workspace:

```text
name: Park Vartopo
location_label: Sofia, Bulgaria
workspace_type: public_observation_area
```

Geometry is stored as GeoJSON text for the SQLite prototype. Weed observations may use approximate `latitude` and `longitude`, rough `geometry_geojson`, or no coordinates at all. The GeoJSON endpoint returns only observations with usable geometry.

Example GeoJSON response:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [23.2852, 42.6581]
      },
      "properties": {
        "species": "Chenopodium album",
        "density_class": "medium",
        "coverage_percent": 35
      }
    }
  ]
}
```

## Known Limitations

- Predictions are rule-based and only use stored observations plus request context.
- There is no authentication yet.
- SQLite stores geometry as plain GeoJSON text; PostGIS is a later target.
- No frontend has been added.
- Weather, soil, crop history, and terrain models are not implemented yet.

## Next Steps

- Add crop season and soil observation endpoints.
- Add map layer models and layer GeoJSON endpoints.
- Add field-level prediction GeoJSON.
- Introduce a small Leaflet frontend after the backend API is stable.
