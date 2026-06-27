# Vartopo Observation Workflow

## Purpose

This document defines the next product phase for Crop Oracle: turning the current map UI into a practical field-observation workflow for Park Vartopo.

The priority is not machine learning yet. The priority is collecting consistent, map-linked observations that will later make prediction possible.

Bad observations create bad models. Bad models create confident nonsense. Humanity has produced enough of that already.

## Product principle

Crop Oracle should make field observation fast enough that it can be used during a walk.

The user should be able to:

1. Open the Vartopo map.
2. Tap or draw an observed plant/weed patch.
3. Fill a short form.
4. Save the observation.
5. Immediately see it on the map.
6. Filter observations by date, species, status, density, and confidence.

The app must support rough observations. A rough polygon with useful notes is better than a perfect form that nobody fills in.

## Observation types

Support these observation geometry types:

- Point: single plant, small patch, quick GPS observation.
- Polygon: patch, area, dense stand, mixed vegetation zone.
- Line: path edge, disturbed strip, drainage line, boundary, walking route.
- Rectangle: quick approximate area.

Each geometry should save as GeoJSON.

## Observation form: phase 2

The current observation form is a good start. Extend it gradually instead of replacing it with a bureaucratic monster.

### Required fields

- Species or label
- Observation date
- Geometry

### Strongly recommended fields

- Confidence
- Coverage percent
- Density class
- Growth stage
- Status / management category
- Notes

### Optional fields

- Plant family
- Native/common name
- Height cm
- Flowering / seeding flag
- Moisture class
- Disturbance class
- Soil exposure percent
- Photo URL or local photo reference
- Tags

## Species or label field

Do not force exact Latin species identification.

The field should allow values such as:

- `Urtica dioica`
- `nettle`
- `possible vetch`
- `unknown grass`
- `yellow flowering Fabaceae`
- `mixed low groundcover`

Store the raw text exactly as entered.

Later, add a normalized species table, but do not block rough data now.

## Status categories

Every observation should eventually have a management/ecological status:

- beneficial
- neutral
- monitor
- aggressive
- unknown

Default should be `unknown` unless inferred client-side for display.

Status meaning:

### beneficial

Plants that may help the system:

- legumes / nitrogen fixers
- pollinator-supporting flowers
- edible/useful plants
- erosion-control groundcover
- biodiversity indicators

### neutral

Low-risk plants that are not currently a problem.

### monitor

Plants that may become competitive, spread, flower, seed, or hide a site condition worth tracking.

### aggressive

Plants or patches that are likely to dominate, spread heavily, compete with crops/experiments, or create a large seed-bank problem.

### unknown

Use when the observation is incomplete.

## Growth stage

Use a small controlled list:

- seedling
- vegetative
- flowering
- seeding
- senescent
- dry_residue
- unknown

This matters more than it looks. A plant before seed and a plant after seed are not the same management problem, because biology enjoys paperwork too.

## Density class

Keep the existing classes:

- low
- medium
- high

Interpretation:

- low: scattered plants or weak patch
- medium: visible patch but not dominant
- high: dominant or near-continuous cover

Coverage percent should remain numeric from 0 to 100.

## Environmental quick tags

Add simple classes that can be selected quickly in the field.

### Moisture class

- dry
- normal
- moist
- wet
- unknown

### Disturbance class

- undisturbed
- footpath_edge
- mowed
- dug
- dumped_material
- construction_edge
- bare_soil
- unknown

### Light class

- full_sun
- partial_shade
- shade
- unknown

These are low-cost features that later become strong predictors.

## Photo handling

Phase 2 can keep URL-based photos if local upload is not implemented yet.

Later add real uploads.

Desired photo model:

- id
- observation_id
- url or file_path
- thumbnail_url or thumbnail_path
- taken_at
- notes

Frontend behavior:

- show thumbnail in popup
- click opens full image
- allow multiple photos later

Do not make photos mandatory. Mandatory photos will slow down data collection.

## Map behavior

### Must-have

- Map opens centered on Park Vartopo.
- Existing observations load automatically.
- New drawn observation saves and appears without full reload.
- Popup shows key fields.
- Layer toggles remain simple.
- Time slider filters observations by month.

### Next filters

Add a filter panel with:

- species text search
- status
- density
- growth stage
- confidence threshold
- date range or month

### Visual styling

Default color mode should be status:

- beneficial: green
- neutral: yellow
- monitor: orange
- aggressive: red
- unknown: blue/gray

Add family color mode later, but it should not replace status as the practical default.

## Observation quality score

Add a simple client-visible quality score later:

- + geometry exists
- + species/label exists
- + confidence set
- + coverage set
- + growth stage set
- + photo exists
- + notes exist

Example labels:

- poor
- usable
- good
- strong

This should guide better observations without shaming the user. The plants are already doing enough judging.

## Backend changes for next implementation

Extend `WeedObservation` gradually with:

- status
- plant_family
- height_cm
- growth_stage, if not already present everywhere
- is_flowering
- is_seeding
- moisture_class
- disturbance_class
- light_class
- soil_exposure_percent
- tags_json

Keep SQLite-compatible fields for now.

Do not introduce migrations unless the project already has migration tooling. If no migration tooling exists, update the schema carefully and document that local DB reset may be needed during prototype development.

## API changes for next implementation

Update observation create/list schemas and GeoJSON properties to include:

- status
- plant_family
- height_cm
- growth_stage
- is_flowering
- is_seeding
- moisture_class
- disturbance_class
- light_class
- soil_exposure_percent
- tags

Add optional filtering query params later:

```text
GET /map/workspaces/{workspace_id}/observations.geojson?species=urtica&status=aggressive&density=high&month=2026-06
```

Do not implement all filters at once if it complicates the code. Start with species, status, density, and month.

## Frontend changes for next implementation

Update the observation dialog:

1. Keep the first section short:
   - species/label
   - date
   - confidence
   - coverage
   - density

2. Add ecological details:
   - status
   - growth stage
   - flowering
   - seeding
   - height cm

3. Add environment:
   - moisture
   - disturbance
   - light
   - soil exposure percent

4. Add notes/photos.

Do not make the form feel like tax software. Use compact sections and reasonable defaults.

## Field workflow for Vartopo

Recommended real-world observation route:

1. Start with walking paths and edges.
2. Record 10 to 20 obvious patches.
3. Include both aggressive and beneficial plants.
4. Record unknowns instead of ignoring them.
5. Use polygons for larger patches.
6. Use points for uncertain plants.
7. Repeat the same route every 2 to 4 weeks.

Minimum useful observation batch:

```text
20 observations
5+ species/labels
at least 5 polygons
at least 5 photos
at least 3 unknowns
```

This gives enough data to test filtering, time changes, density display, and rough prediction behavior.

## Implementation order for Codex

### Task 1: extend observation schema

- Add status and environmental quick tags to backend model/schema.
- Include them in API create/list responses.
- Include them in GeoJSON properties.
- Add tests.

### Task 2: update frontend form

- Add new fields to the observation dialog.
- Send them to the API.
- Show them in popups.
- Color by explicit status when present.
- Fall back to inferred status only when explicit status is missing.

### Task 3: add map filters

- Add filter controls for species text, status, density, growth stage, and confidence threshold.
- Apply filters client-side first.
- Keep server-side filters for later.

### Task 4: add observation quality indicator

- Compute quality client-side from fields.
- Show quality in popup and optionally in observation list later.

## Acceptance criteria for phase 2

Phase 2 is acceptable when:

- A user can walk in Vartopo and add useful rough observations from the map.
- Observations can be drawn as point, polygon, line, or rectangle.
- Observations show status, density, coverage, growth stage, confidence, and notes.
- The map can be filtered enough to find useful patterns.
- GeoJSON export contains enough properties for later analysis.
- Tests still pass.

## Non-goals for this phase

Do not implement yet:

- real ML
- image recognition
- satellite imagery import
- DEM processing
- PostGIS migration
- authentication
- mobile app packaging
- offline sync

All of those are useful later. Doing them now would be how a promising tool becomes a museum of unfinished features.
