from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class MapWorkspace(Base):
    __tablename__ = "map_workspaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    workspace_type: Mapped[str] = mapped_column(String(80), nullable=False)
    location_label: Mapped[str | None] = mapped_column(String(160))
    center_latitude: Mapped[float | None] = mapped_column(Float)
    center_longitude: Mapped[float | None] = mapped_column(Float)
    default_zoom: Mapped[int] = mapped_column(Integer, default=14)
    boundary_geojson: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    fields: Mapped[list["Field"]] = relationship(back_populates="workspace")
    observations: Mapped[list["WeedObservation"]] = relationship(back_populates="workspace")


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("map_workspaces.id"))
    name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    location_label: Mapped[str | None] = mapped_column(String(160))
    approximate_latitude: Mapped[float | None] = mapped_column(Float)
    approximate_longitude: Mapped[float | None] = mapped_column(Float)
    area_square_meters: Mapped[float | None] = mapped_column(Float)
    boundary_geojson: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    workspace: Mapped[MapWorkspace | None] = relationship(back_populates="fields")
    observations: Mapped[list["WeedObservation"]] = relationship(back_populates="field")
    prediction_runs: Mapped[list["PredictionRun"]] = relationship(back_populates="field")


class WeedObservation(Base):
    __tablename__ = "weed_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    workspace_id: Mapped[int | None] = mapped_column(ForeignKey("map_workspaces.id"))
    field_id: Mapped[int | None] = mapped_column(ForeignKey("fields.id"))
    field_cell_id: Mapped[int | None] = mapped_column(Integer)
    observed_at: Mapped[date] = mapped_column(Date, nullable=False)
    species: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    confidence: Mapped[float | None] = mapped_column(Float)
    coverage_percent: Mapped[float | None] = mapped_column(Float)
    density_class: Mapped[str | None] = mapped_column(String(40))
    average_height_cm: Mapped[float | None] = mapped_column(Float)
    growth_stage: Mapped[str | None] = mapped_column(String(80))
    crop_nearby: Mapped[str | None] = mapped_column(String(120))
    photo_reference: Mapped[str | None] = mapped_column(String(300))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    geometry_geojson: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    workspace: Mapped[MapWorkspace | None] = relationship(back_populates="observations")
    field: Mapped[Field | None] = relationship(back_populates="observations")


class PredictionRun(Base):
    __tablename__ = "prediction_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    target_year: Mapped[int] = mapped_column(Integer, nullable=False)
    model_name: Mapped[str] = mapped_column(String(120), default="rule_based")
    model_version: Mapped[str] = mapped_column(String(40), default="0.1.0")
    notes: Mapped[str | None] = mapped_column(Text)

    field: Mapped[Field] = relationship(back_populates="prediction_runs")
    predictions: Mapped[list["WeedPrediction"]] = relationship(back_populates="prediction_run")


class WeedPrediction(Base):
    __tablename__ = "weed_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    prediction_run_id: Mapped[int] = mapped_column(ForeignKey("prediction_runs.id"), nullable=False)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"), nullable=False)
    field_cell_id: Mapped[int | None] = mapped_column(Integer)
    species: Mapped[str] = mapped_column(String(160), nullable=False)
    probability: Mapped[float] = mapped_column(Float, nullable=False)
    expected_density_class: Mapped[str] = mapped_column(String(40), nullable=False)
    expected_coverage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    emergence_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    emergence_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    competition_risk: Mapped[str] = mapped_column(String(40), nullable=False)
    coexistence_recommendation: Mapped[str] = mapped_column(String(40), nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    prediction_run: Mapped[PredictionRun] = relationship(back_populates="predictions")
