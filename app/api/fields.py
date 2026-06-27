from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.session import get_db
from app.models import Field, ObservationPhoto, PredictionRun, WeedObservation
from app.schemas.domain import (
    FieldCreate,
    FieldRead,
    PredictionRequest,
    PredictionRunRead,
    WeedObservationCreate,
    WeedObservationRead,
)
from app.services.prediction import run_rule_based_prediction

router = APIRouter(prefix="/fields", tags=["fields"])


def _get_field_or_404(db: Session, field_id: int) -> Field:
    field = db.get(Field, field_id)
    if field is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Field not found")
    return field


@router.post("", response_model=FieldRead, status_code=status.HTTP_201_CREATED)
def create_field(payload: FieldCreate, db: Session = Depends(get_db)) -> Field:
    field = Field(**payload.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.get("", response_model=list[FieldRead])
def list_fields(db: Session = Depends(get_db)) -> list[Field]:
    return list(db.scalars(select(Field).order_by(Field.created_at.desc(), Field.id.desc())))


@router.get("/{field_id}", response_model=FieldRead)
def get_field(field_id: int, db: Session = Depends(get_db)) -> Field:
    return _get_field_or_404(db, field_id)


@router.post(
    "/{field_id}/weed-observations",
    response_model=WeedObservationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_weed_observation(
    field_id: int,
    payload: WeedObservationCreate,
    db: Session = Depends(get_db),
) -> WeedObservation:
    field = _get_field_or_404(db, field_id)
    observation_data = payload.model_dump()
    photos = observation_data.pop("photos", [])
    observation_data["workspace_id"] = (
        payload.workspace_id if payload.workspace_id is not None else field.workspace_id
    )
    observation = WeedObservation(
        **observation_data,
        field_id=field.id,
    )
    observation.photos = [ObservationPhoto(**photo) for photo in photos]
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


@router.get("/{field_id}/weed-observations", response_model=list[WeedObservationRead])
def list_weed_observations(field_id: int, db: Session = Depends(get_db)) -> list[WeedObservation]:
    _get_field_or_404(db, field_id)
    statement = (
        select(WeedObservation)
        .options(selectinload(WeedObservation.photos))
        .where(WeedObservation.field_id == field_id)
        .order_by(WeedObservation.observed_at.desc(), WeedObservation.id.desc())
    )
    return list(db.scalars(statement))


@router.post("/{field_id}/predict", response_model=PredictionRunRead)
def predict_field(
    field_id: int,
    payload: PredictionRequest,
    db: Session = Depends(get_db),
) -> PredictionRun:
    field = _get_field_or_404(db, field_id)
    observations = list(
        db.scalars(select(WeedObservation).where(WeedObservation.field_id == field_id))
    )
    return run_rule_based_prediction(db, field, payload, observations)


@router.get("/{field_id}/predictions/latest", response_model=PredictionRunRead)
def get_latest_prediction(field_id: int, db: Session = Depends(get_db)) -> PredictionRun:
    _get_field_or_404(db, field_id)
    statement = (
        select(PredictionRun)
        .options(selectinload(PredictionRun.predictions))
        .where(PredictionRun.field_id == field_id)
        .order_by(PredictionRun.run_at.desc(), PredictionRun.id.desc())
    )
    prediction_run = db.scalar(statement)
    if prediction_run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prediction not found")
    return prediction_run
