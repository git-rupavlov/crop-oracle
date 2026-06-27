from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MapLayer, MapWorkspace


DEFAULT_LAYERS = [
    {
        "name": "Observations",
        "layer_type": "observations",
        "geometry_type": "mixed",
        "source_type": "observations",
        "style_json": '{"color": "#3b8f5c"}',
        "notes": "Observed weed points and drawn areas.",
    },
    {
        "name": "Predicted weeds",
        "layer_type": "predicted_weeds",
        "geometry_type": "polygon",
        "source_type": "generated",
        "style_json": '{"color": "#d9480f"}',
        "notes": "Generated placeholder for weed-pressure predictions.",
    },
    {
        "name": "Terrain",
        "layer_type": "terrain",
        "geometry_type": "polygon",
        "source_type": "environmental",
        "style_json": '{"color": "#6c757d"}',
        "notes": "Future terrain, slope, aspect, and elevation layer.",
    },
    {
        "name": "Moisture",
        "layer_type": "moisture",
        "geometry_type": "polygon",
        "source_type": "environmental",
        "style_json": '{"color": "#1c7ed6"}',
        "notes": "Future wet-zone and moisture indicators.",
    },
    {
        "name": "Disturbance",
        "layer_type": "disturbance",
        "geometry_type": "polygon",
        "source_type": "observation",
        "style_json": '{"color": "#f08c00"}',
        "notes": "Future disturbed soil, edges, and unmanaged-zone layer.",
    },
    {
        "name": "Experiment plots",
        "layer_type": "experiment_plots",
        "geometry_type": "polygon",
        "source_type": "observation",
        "style_json": '{"color": "#7048e8"}',
        "notes": "Future crop or ecological experiment zones.",
    },
    {
        "name": "Walking paths",
        "layer_type": "walking_paths",
        "geometry_type": "line",
        "source_type": "osm",
        "style_json": '{"color": "#495057"}',
        "notes": "Future OpenStreetMap walking path imports.",
    },
]


def seed_default_workspace(db: Session) -> None:
    existing = db.scalar(select(MapWorkspace).where(MapWorkspace.name == "Park Vartopo"))
    if existing:
        return

    workspace = MapWorkspace(
        name="Park Vartopo",
        location_label="Sofia, Bulgaria",
        workspace_type="public_observation_area",
        center_latitude=42.658,
        center_longitude=23.285,
        default_zoom=14,
        notes=(
            "First pilot area for weed, terrain, moisture, disturbance, "
            "and plant coexistence observations."
        ),
    )
    db.add(workspace)
    db.flush()

    for layer in DEFAULT_LAYERS:
        db.add(MapLayer(workspace_id=workspace.id, visible_by_default=True, **layer))

    db.commit()


def seed_default_layers(db: Session) -> None:
    workspace = db.scalar(select(MapWorkspace).where(MapWorkspace.name == "Park Vartopo"))
    if workspace is None:
        return

    existing_types = set(
        db.scalars(select(MapLayer.layer_type).where(MapLayer.workspace_id == workspace.id))
    )
    for layer in DEFAULT_LAYERS:
        if layer["layer_type"] in existing_types:
            continue
        db.add(MapLayer(workspace_id=workspace.id, visible_by_default=True, **layer))
    db.commit()


def init_db(db: Session) -> None:
    seed_default_workspace(db)
    seed_default_layers(db)
