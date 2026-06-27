import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import MapWorkspace, WeedObservation
from app.schemas.domain import GeoJSONFeatureCollection, MapWorkspaceCreate, MapWorkspaceRead

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
        .where(WeedObservation.workspace_id == workspace_id)
        .order_by(WeedObservation.observed_at.desc(), WeedObservation.id.desc())
    )
    features = []
    for observation in observations:
        geometry = _observation_geometry(observation)
        if geometry is None:
            continue
        features.append(
            {
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
                    "growth_stage": observation.growth_stage,
                    "notes": observation.notes,
                },
            }
        )

    return {"type": "FeatureCollection", "features": features}
