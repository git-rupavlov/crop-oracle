import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import MapLayer, MapWorkspace, ObservationPhoto, WeedObservation
from app.schemas.domain import (
    GeoJSONFeatureCollection,
    MapLayerCreate,
    MapLayerRead,
    MapWorkspaceCreate,
    MapWorkspaceRead,
    WeedObservationCreate,
    WeedObservationRead,
)

router = APIRouter(prefix="/map", tags=["map"])


@router.post("/workspaces", response_model=MapWorkspaceRead, status_code=status.HTTP_201_CREATED)
def create_workspace(payload: MapWorkspaceCreate, db: Session = Depends(get_db)) -> MapWorkspace:
    workspace = MapWorkspace(**payload.model_dump())
    db.add(workspace)
    db.commit()
    db.refresh(workspace)
    return workspace


@router.get("/workspaces", response_model=list[MapWorkspaceRead])
def list_workspaces(db: Session = Depends(get_db)) -> list[MapWorkspace]:
    return list(db.scalars(select(MapWorkspace).order_by(MapWorkspace.name)))


@router.get("/workspaces/{workspace_id}", response_model=MapWorkspaceRead)
def get_workspace(workspace_id: int, db: Session = Depends(get_db)) -> MapWorkspace:
    workspace = db.get(MapWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def _get_workspace_or_404(db: Session, workspace_id: int) -> MapWorkspace:
    workspace = db.get(MapWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return workspace


def _dump_observation_payload(payload: WeedObservationCreate) -> tuple[dict, list[dict]]:
    observation_data = payload.model_dump()
    photos = observation_data.pop("photos", [])
    tags = observation_data.pop("tags", [])
    observation_data["tags_json"] = json.dumps(tags) if tags else None
    return observation_data, photos


@router.post(
    "/workspaces/{workspace_id}/observations",
    response_model=WeedObservationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_workspace_observation(
    workspace_id: int,
    payload: WeedObservationCreate,
    db: Session = Depends(get_db),
) -> WeedObservation:
    _get_workspace_or_404(db, workspace_id)
    observation_data, photos = _dump_observation_payload(payload)
    observation_data.pop("workspace_id", None)
    observation = WeedObservation(
        **observation_data,
        workspace_id=workspace_id,
    )
    observation.photos = [ObservationPhoto(**photo) for photo in photos]
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


@router.get("/workspaces/{workspace_id}/layers", response_model=list[MapLayerRead])
def list_layers(workspace_id: int, db: Session = Depends(get_db)) -> list[MapLayer]:
    _get_workspace_or_404(db, workspace_id)
    statement = select(MapLayer).where(MapLayer.workspace_id == workspace_id).order_by(MapLayer.id)
    return list(db.scalars(statement))


@router.post(
    "/workspaces/{workspace_id}/layers",
    response_model=MapLayerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_layer(
    workspace_id: int,
    payload: MapLayerCreate,
    db: Session = Depends(get_db),
) -> MapLayer:
    _get_workspace_or_404(db, workspace_id)
    layer = MapLayer(workspace_id=workspace_id, **payload.model_dump())
    db.add(layer)
    db.commit()
    db.refresh(layer)
    return layer


def _observation_geometry(observation: WeedObservation) -> dict[str, Any] | None:
    if observation.geometry_geojson:
        try:
            geometry = json.loads(observation.geometry_geojson)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Observation {observation.id} has invalid geometry GeoJSON",
            ) from exc
        if geometry.get("type") == "Feature":
            return geometry.get("geometry")
        return geometry
    if observation.latitude is not None and observation.longitude is not None:
        return {
            "type": "Point",
            "coordinates": [observation.longitude, observation.latitude],
        }
    return None


def _observation_feature(observation: WeedObservation) -> dict[str, Any] | None:
    geometry = _observation_geometry(observation)
    if geometry is None:
        return None
    photos = [
        {
            "id": photo.id,
            "url": photo.url,
            "thumbnail_url": photo.thumbnail_url,
            "taken_at": photo.taken_at.isoformat() if photo.taken_at else None,
            "notes": photo.notes,
        }
        for photo in observation.photos
    ]
    if observation.photo_reference and not photos:
        photos.append(
            {
                "id": None,
                "url": observation.photo_reference,
                "thumbnail_url": observation.photo_reference,
                "taken_at": None,
                "notes": None,
            }
        )
    return {
        "type": "Feature",
        "geometry": geometry,
        "properties": {
            "id": observation.id,
            "field_id": observation.field_id,
            "species": observation.species,
            "observed_at": observation.observed_at.isoformat(),
            "confidence": observation.confidence,
            "coverage_percent": observation.coverage_percent,
            "density_class": observation.density_class,
            "status": observation.status,
            "plant_family": observation.plant_family,
            "average_height_cm": observation.average_height_cm,
            "height_cm": observation.height_cm,
            "growth_stage": observation.growth_stage,
            "is_flowering": observation.is_flowering,
            "is_seeding": observation.is_seeding,
            "moisture_class": observation.moisture_class,
            "disturbance_class": observation.disturbance_class,
            "light_class": observation.light_class,
            "soil_exposure_percent": observation.soil_exposure_percent,
            "tags": observation.tags,
            "photo_reference": observation.photo_reference,
            "photos": photos,
            "notes": observation.notes,
        },
    }


def _empty_layer_geojson(layer: MapLayer) -> dict[str, Any]:
    return {
        "type": "FeatureCollection",
        "features": [],
        "properties": {
            "layer_id": layer.id,
            "layer_type": layer.layer_type,
            "name": layer.name,
            "status": "placeholder",
        },
    }


@router.get(
    "/workspaces/{workspace_id}/observations.geojson", response_model=GeoJSONFeatureCollection
)
def workspace_observations_geojson(
    workspace_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    workspace = db.get(MapWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    observations = db.scalars(
        select(WeedObservation)
        .options(selectinload(WeedObservation.photos))
        .where(WeedObservation.workspace_id == workspace_id)
        .order_by(WeedObservation.observed_at.desc(), WeedObservation.id.desc())
    )
    features = []
    for observation in observations:
        feature = _observation_feature(observation)
        if feature:
            features.append(feature)

    return {"type": "FeatureCollection", "features": features}


@router.get(
    "/workspaces/{workspace_id}/layers/{layer_id}/geojson",
    response_model=GeoJSONFeatureCollection,
)
def layer_geojson(
    workspace_id: int,
    layer_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _get_workspace_or_404(db, workspace_id)
    layer = db.get(MapLayer, layer_id)
    if layer is None or layer.workspace_id != workspace_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Layer not found")
    if layer.layer_type == "observations":
        return workspace_observations_geojson(workspace_id, db)
    return _empty_layer_geojson(layer)
