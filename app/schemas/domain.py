from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


DensityClass = Literal["low", "medium", "high"]
RiskClass = Literal["low", "medium", "high"]
Recommendation = Literal["tolerate", "monitor", "suppress"]


class FieldBase(BaseModel):
    workspace_id: int | None = None
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    location_label: str | None = Field(default=None, max_length=160)
    approximate_latitude: float | None = Field(default=None, ge=-90, le=90)
    approximate_longitude: float | None = Field(default=None, ge=-180, le=180)
    area_square_meters: float | None = Field(default=None, ge=0)
    boundary_geojson: str | None = None
    notes: str | None = None


class FieldCreate(FieldBase):
    pass


class FieldRead(FieldBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeedObservationBase(BaseModel):
    workspace_id: int | None = None
    field_cell_id: int | None = None
    observed_at: date
    species: str = Field(min_length=1, max_length=160)
    confidence: float | None = Field(default=None, ge=0, le=1)
    coverage_percent: float | None = Field(default=None, ge=0, le=100)
    density_class: DensityClass | None = None
    average_height_cm: float | None = Field(default=None, ge=0)
    growth_stage: str | None = Field(default=None, max_length=80)
    crop_nearby: str | None = Field(default=None, max_length=120)
    photo_reference: str | None = Field(default=None, max_length=300)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    geometry_geojson: str | None = None
    notes: str | None = None


class ObservationPhotoBase(BaseModel):
    url: str = Field(min_length=1, max_length=500)
    thumbnail_url: str | None = Field(default=None, max_length=500)
    taken_at: datetime | None = None
    notes: str | None = None


class ObservationPhotoCreate(ObservationPhotoBase):
    pass


class ObservationPhotoRead(ObservationPhotoBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WeedObservationCreate(WeedObservationBase):
    photos: list[ObservationPhotoCreate] = Field(default_factory=list)


class WeedObservationRead(WeedObservationBase):
    id: int
    field_id: int | None
    created_at: datetime
    photos: list[ObservationPhotoRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PredictionRequest(BaseModel):
    target_year: int = Field(ge=2000, le=2100)
    recent_rainfall_mm: float | None = Field(default=None, ge=0)
    recent_mean_temp_c: float | None = None
    disturbed_soil: bool = False
    crop_established: bool = False


class WeedPredictionRead(BaseModel):
    id: int
    field_id: int
    species: str
    probability: float = Field(ge=0, le=1)
    expected_density_class: DensityClass
    expected_coverage_percent: float
    emergence_start_date: date
    emergence_end_date: date
    competition_risk: RiskClass
    coexistence_recommendation: Recommendation
    reasoning: str

    model_config = ConfigDict(from_attributes=True)


class PredictionRunRead(BaseModel):
    id: int
    field_id: int
    run_at: datetime
    target_year: int
    model_name: str
    model_version: str
    notes: str | None
    predictions: list[WeedPredictionRead]

    model_config = ConfigDict(from_attributes=True)


class MapWorkspaceBase(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    workspace_type: str = Field(min_length=1, max_length=80)
    location_label: str | None = Field(default=None, max_length=160)
    center_latitude: float | None = Field(default=None, ge=-90, le=90)
    center_longitude: float | None = Field(default=None, ge=-180, le=180)
    default_zoom: int = Field(default=14, ge=1, le=22)
    boundary_geojson: str | None = None
    notes: str | None = None


class MapWorkspaceCreate(MapWorkspaceBase):
    pass


class MapWorkspaceRead(MapWorkspaceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MapLayerBase(BaseModel):
    field_id: int | None = None
    name: str = Field(min_length=1, max_length=160)
    layer_type: str = Field(min_length=1, max_length=80)
    geometry_type: str = Field(min_length=1, max_length=80)
    source_type: str = Field(default="generated", min_length=1, max_length=80)
    style_json: str | None = None
    visible_by_default: bool = True
    notes: str | None = None


class MapLayerCreate(MapLayerBase):
    pass


class MapLayerRead(MapLayerBase):
    id: int
    workspace_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: list[dict[str, Any]]
