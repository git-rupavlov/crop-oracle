# AGENTS.md

## Project goal
Build **Crop Oracle**, an application for predicting weed species and weed pressure based on:

- weather history and forecast
- terrain and GIS data
- soil observations
- crop history
- last-year weed observations
- management practices such as tillage, mulch, compost, cover crops, mowing, grazing, and irrigation

Primary goal: improve crop planning and support coexistence between crops and useful or non-damaging weeds. The app should help decide which weeds can remain, which should be controlled, and when intervention matters.

The first real-world pilot area is **park Vartopo / Vartopo field area in Sofia, Bulgaria**. Treat this as the initial observation and visualization area, not as a private farm field.

## Product direction
This is not a herbicide-first application. Treat weeds as field indicators and ecological actors, not only as enemies.

The application should answer questions like:

- Which weed species are likely to appear in this field this season?
- When are they likely to emerge?
- Which field zones have the highest weed pressure?
- Which weeds are likely to compete strongly with the planned crop?
- Which weeds may be tolerated as living mulch, erosion control, pollinator support, or soil indicators?
- Which observations should be collected next to improve predictions?
- How do observations, terrain, moisture, soil, paths, and predicted weed pressure look together on a map?

## Map-first visualization direction
Crop Oracle should become a map-based observation and planning tool.

The map is not decoration. It is the primary way to understand the data.

Start with **park Vartopo** as the first map workspace. The app should support public/natural area observations first, then later crop plots, balcony beds, greenhouse beds, and future farm fields.

### Map goals
The map should allow layered visualization of:

- field or park boundary
- observation points
- weed species observations
- plant coverage percent
- density class
- growth stage
- observation confidence
- terrain slope/aspect/elevation
- moisture or wet-zone indicators
- paths, disturbed areas, edges, and unmanaged zones
- crop/experiment zones, when relevant
- predicted weed pressure grid
- coexistence recommendation: tolerate, monitor, suppress

### Frontend map stack
When a frontend is introduced, prefer:

- Leaflet for the first simple implementation
- MapLibre GL if vector tiles, heavier styling, or larger spatial datasets become necessary
- OpenStreetMap as the default basemap
- GeoJSON as the first interchange format

Do not introduce a heavy GIS server in the first version. Start with API-generated GeoJSON and a simple browser map. Humanity already invented enough infrastructure-shaped suffering.

### Map layer model
Add a `MapLayer` concept when needed.

Suggested fields:

- id
- field_id, optional
- name
- layer_type
- geometry_type
- source_type
- style_json
- visible_by_default
- created_at
- notes

Useful layer types:

- boundary
- observation_points
- weed_species
- density
- coverage
- terrain
- moisture
- disturbance
- prediction_grid
- coexistence

### Spatial data format
For the SQLite prototype:

- store geometry as GeoJSON text
- use WGS84 coordinates, EPSG:4326
- keep exact private coordinates optional
- allow approximate coordinates or hand-drawn areas

For PostgreSQL/PostGIS later:

- use proper geometry columns
- add spatial indexes
- support bounding-box queries
- support field-cell grid generation

### Map API expectations
Add these endpoints when the core backend exists:

```text
GET    /map/workspaces
POST   /map/workspaces
GET    /map/workspaces/{workspace_id}
GET    /map/workspaces/{workspace_id}/layers
POST   /map/workspaces/{workspace_id}/layers
GET    /map/workspaces/{workspace_id}/layers/{layer_id}/geojson
GET    /fields/{field_id}/map/observations.geojson
GET    /fields/{field_id}/map/predictions.geojson
GET    /fields/{field_id}/map/cells.geojson
```

The first map workspace should be seeded as:

```text
name: Park Vartopo
location_label: Sofia, Bulgaria
workspace_type: public_observation_area
notes: First pilot area for weed, terrain, moisture, disturbance, and plant coexistence observations.
```

Use approximate public-area geometry unless exact boundaries are intentionally added later.

### First map UI behavior
When the frontend exists, implement:

- map centered around park Vartopo
- layer toggle panel
- clickable observation markers
- popup with species, date, coverage, density, confidence, notes
- color/style by density or recommendation
- simple legend
- GeoJSON export

Do not start with satellite processing, vector tiles, advanced routing, or drone-data dreams. First show the observations on a map. Then earn complexity.

## Behavior rules for coding agents
- Plan before coding.
- Make small, reviewable changes.
- Do not rewrite unrelated code.
- Prefer a simple working implementation over over-engineered architecture.
- Explain assumptions briefly in commit messages or task summaries.
- Never commit secrets, API keys, tokens, private addresses, or precise private land coordinates.
- Keep code readable and boring. Boring code survives longer than clever code, because humans keep maintaining software for some reason.
- Add tests when adding behavior.
- Update documentation when changing commands, setup, schema, public APIs, or map behavior.

## Initial tech stack
Use this stack unless there is a clear reason to change it:

- Python 3.11+
- FastAPI for backend API
- SQLAlchemy 2.x for ORM
- Pydantic 2.x for request/response models
- SQLite for the first local prototype
- PostgreSQL + PostGIS as the later production target
- Pandas / GeoPandas for data handling when needed
- scikit-learn for the first ML models
- Leaflet for the first map frontend
- OpenStreetMap basemap
- GeoJSON for spatial API responses
- Docker Compose for local development once the backend skeleton exists
- pytest for tests
- ruff for linting and formatting

Start API and data model first. Add a very small map frontend only after the core observation API exists.

## Architecture preference
Start as a modular monolith:

```text
crop-oracle/
  app/
    main.py
    api/
    core/
    db/
    models/
    schemas/
    services/
    ml/
    map/
  frontend/
    # only when map UI is introduced
  tests/
  scripts/
  docs/
```

Avoid microservices until the application has real usage and actual scaling pain. Pretending to be Netflix before having one field record is how software becomes compost.

## Core domain entities
Implement these concepts gradually:

### MapWorkspace
A spatial workspace for a field, park, balcony, greenhouse, or experimental area.

Suggested fields:

- id
- name
- workspace_type
- location_label
- center_latitude, optional
- center_longitude, optional
- default_zoom
- boundary_geojson, optional
- notes
- created_at

### MapLayer
A user-visible map layer.

Suggested fields:

- id
- workspace_id
- field_id, optional
- name
- layer_type
- geometry_type
- source_type
- style_json
- visible_by_default
- notes
- created_at

### Field
A registered field, plot, balcony bed, greenhouse bed, or experimental area.

Suggested fields:

- id
- workspace_id, optional
- name
- description
- location label
- approximate latitude/longitude, optional
- area square meters, optional
- boundary_geojson, optional
- notes
- created_at

### FieldCell
A spatial subdivision of a field for grid-based prediction.

Suggested fields:

- id
- field_id
- cell_code
- geometry_geojson
- slope
- aspect
- elevation
- moisture_class
- soil_texture
- notes

For SQLite prototype, geometry should be stored as GeoJSON text.

### CropSeason
A crop plan or crop history entry.

Suggested fields:

- id
- field_id
- year
- crop_name
- variety
- planting_date
- expected_harvest_date
- management_notes

### WeedObservation
A field observation of weeds.

Suggested fields:

- id
- workspace_id, optional
- field_id, optional
- field_cell_id, optional
- observed_at
- species
- confidence
- coverage_percent
- density_class
- average_height_cm
- growth_stage
- crop_nearby
- photo_reference
- latitude, optional
- longitude, optional
- geometry_geojson, optional
- notes

A weed observation may be a point, polygon, or rough area. Do not force every observation to be a perfect GPS point.

### WeatherDaily
Daily weather data used as features.

Suggested fields:

- id
- field_id or station_id
- date
- temp_min_c
- temp_max_c
- temp_mean_c
- rainfall_mm
- humidity_percent
- wind_speed_mps
- solar_radiation_mj_m2
- soil_temp_c, optional

### SoilObservation
Soil measurements or field notes.

Suggested fields:

- id
- field_id
- field_cell_id, optional
- observed_at
- ph
- organic_matter_percent
- nitrogen_level
- phosphorus_level
- potassium_level
- texture
- compaction
- drainage
- latitude, optional
- longitude, optional
- geometry_geojson, optional
- notes

### PredictionRun
A prediction execution event.

Suggested fields:

- id
- field_id
- run_at
- target_year
- model_name
- model_version
- notes

### WeedPrediction
Prediction output per weed species and optional field cell.

Suggested fields:

- id
- prediction_run_id
- field_id
- field_cell_id, optional
- species
- probability
- expected_density_class
- expected_coverage_percent
- emergence_start_date
- emergence_end_date
- competition_risk
- coexistence_recommendation
- reasoning

## API expectations
Implement endpoints gradually.

First version:

```text
GET    /health
POST   /fields
GET    /fields
GET    /fields/{field_id}
POST   /fields/{field_id}/weed-observations
GET    /fields/{field_id}/weed-observations
POST   /fields/{field_id}/predict
GET    /fields/{field_id}/predictions/latest
```

Map-capable first version, after basic CRUD:

```text
POST   /map/workspaces
GET    /map/workspaces
GET    /map/workspaces/{workspace_id}
GET    /map/workspaces/{workspace_id}/observations.geojson
GET    /map/workspaces/{workspace_id}/layers
GET    /map/workspaces/{workspace_id}/layers/{layer_id}/geojson
```

Later:

```text
POST   /fields/{field_id}/crop-seasons
POST   /fields/{field_id}/soil-observations
POST   /fields/{field_id}/weather-daily/import
GET    /fields/{field_id}/export/geojson
GET    /fields/{field_id}/export/csv
```

## Prediction approach
Start with a baseline rule-based model before ML.

Version 0 rule-based model:

- Previous observation of the same species strongly increases probability.
- High last-year coverage increases expected density.
- Recent rainfall increases probability for moisture-loving annuals.
- Warm soil or warm recent temperatures increase probability for summer annuals such as Amaranthus and Chenopodium.
- Disturbed soil increases annual weed pressure.
- Perennial weed observations should persist across years unless explicitly controlled.

The rule-based model should return:

- species
- probability
- expected density class: low, medium, high
- emergence window
- competition risk: low, medium, high
- coexistence recommendation: tolerate, monitor, suppress
- short reasoning string

Later ML approach:

- RandomForestClassifier for species presence
- RandomForestRegressor or ordinal classifier for density/coverage
- Features from previous observations, weather windows, crop history, soil, terrain, and management
- Keep explainability simple using feature importance and generated reason labels

Do not start with neural networks unless there is enough real field data to justify it.

## Weed coexistence logic
The app should not automatically mark every weed as bad.

A weed may be recommended as **tolerate** when:

- coverage is low
- competition risk is low
- crop is established
- species provides soil cover
- species supports pollinators
- species is edible/useful
- species indicates useful soil information

A weed may be recommended as **monitor** when:

- density is uncertain
- species can become competitive later
- crop is young
- weather favors rapid growth

A weed may be recommended as **suppress** when:

- competition risk is high
- species is perennial and spreading aggressively
- species can overtop the crop
- species hosts important pests or diseases
- species is toxic or unsafe
- seed production would create a large future seed-bank problem

## Data quality rules
- Allow uncertain species identification.
- Store confidence separately from species name.
- Do not discard rough observations. Rough field notes are still useful.
- Prefer structured fields plus free-text notes.
- Avoid requiring perfect GIS data for the first version.
- Keep units metric.
- Allow rough hand-drawn polygons and approximate map points.

## Security and privacy
- Do not commit precise private coordinates by default.
- Use approximate location labels unless the user explicitly chooses exact coordinates.
- Public park observations may use approximate or public map coordinates.
- Keep API keys in environment variables.
- Add `.env` to `.gitignore` when environment files are introduced.

## Testing
Add tests for:

- API health endpoint
- field creation and listing
- weed observation creation and listing
- prediction output shape
- rule-based prediction behavior
- validation errors
- GeoJSON response validity
- map workspace creation and listing

Use pytest.

## Commands to maintain
When the relevant files exist, keep these commands working:

```bash
pytest
ruff check .
ruff format .
uvicorn app.main:app --reload
```

Later, when Docker is added:

```bash
docker compose up --build
```

## Documentation expectations
Maintain `README.md` with:

- project purpose
- local setup
- run commands
- test commands
- API examples
- map/layer explanation
- GeoJSON examples
- known limitations
- next steps

## First Codex task recommendation
When starting from an empty repository, implement this first:

```text
Read AGENTS.md. Build the first minimal working version of Crop Oracle.

Start with:
1. FastAPI backend
2. SQLAlchemy models
3. SQLite for local development
4. CRUD for fields and weed observations
5. Simple rule-based prediction endpoint
6. Seed a default map workspace named Park Vartopo
7. Add GeoJSON output for observations
8. README with run instructions
9. Basic tests

Do not add frontend yet.
```

## Second Codex task recommendation
After the backend exists, implement the first minimal map UI:

```text
Read AGENTS.md. Add a minimal Leaflet frontend for Crop Oracle.

Requirements:
1. Show OpenStreetMap basemap.
2. Center the map on Park Vartopo, Sofia.
3. Load observations from the GeoJSON endpoint.
4. Show layer toggles for observations and prediction grid.
5. Show popups for weed observations.
6. Add a simple legend for density and coexistence recommendation.
7. Keep the frontend small and boring.
```

## Completion report format
When finishing a task, report:

- changed files
- what was implemented
- how to run it
- how to test it
- known limitations
