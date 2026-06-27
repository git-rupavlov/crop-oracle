from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.models import Field, PredictionRun, WeedObservation, WeedPrediction
from app.schemas.domain import PredictionRequest


SUMMER_ANNUAL_HINTS = ("amaranthus", "chenopodium", "pigweed", "lambsquarters")
PERENNIAL_HINTS = ("bindweed", "cirsium", "thistle", "rumex", "dock", "dandelion")
USEFUL_LOW_PRESSURE_HINTS = ("clover", "trifolium", "plantain", "chickweed", "vetch")


def _density_from_coverage(coverage: float) -> str:
    if coverage >= 40:
        return "high"
    if coverage >= 12:
        return "medium"
    return "low"


def _risk_from_density(density: str, perennial: bool) -> str:
    if density == "high" or perennial:
        return "high"
    if density == "medium":
        return "medium"
    return "low"


def _recommendation(species: str, density: str, risk: str, crop_established: bool) -> str:
    species_key = species.lower()
    useful_low_pressure = any(hint in species_key for hint in USEFUL_LOW_PRESSURE_HINTS)
    if risk == "high" or density == "high":
        return "suppress"
    if useful_low_pressure and density == "low" and crop_established:
        return "tolerate"
    return "monitor"


def run_rule_based_prediction(
    db: Session,
    field: Field,
    request: PredictionRequest,
    observations: list[WeedObservation],
) -> PredictionRun:
    grouped: dict[str, list[WeedObservation]] = defaultdict(list)
    for observation in observations:
        grouped[observation.species].append(observation)

    if not grouped:
        grouped["unknown annual weeds"] = []

    prediction_run = PredictionRun(
        field_id=field.id,
        target_year=request.target_year,
        model_name="rule_based",
        model_version="0.1.0",
        notes="Baseline rule-based prediction from stored observations and request context.",
    )
    db.add(prediction_run)
    db.flush()

    for species, species_observations in grouped.items():
        latest_coverage = max(
            (observation.coverage_percent or 0 for observation in species_observations),
            default=5,
        )
        observed_before = bool(species_observations)
        species_key = species.lower()
        perennial = any(hint in species_key for hint in PERENNIAL_HINTS)
        summer_annual = any(hint in species_key for hint in SUMMER_ANNUAL_HINTS)

        probability = 0.25
        reasons = ["baseline uncertainty for a minimally trained prototype"]
        if observed_before:
            probability += 0.35
            reasons.append("previous observations of this species in the field")
        if latest_coverage >= 25:
            probability += 0.15
            reasons.append("high previous coverage")
        if request.recent_rainfall_mm is not None and request.recent_rainfall_mm >= 20:
            probability += 0.10
            reasons.append("recent rainfall favors emergence")
        if (
            request.recent_mean_temp_c is not None
            and request.recent_mean_temp_c >= 18
            and summer_annual
        ):
            probability += 0.10
            reasons.append("warm recent temperatures favor summer annuals")
        if request.disturbed_soil:
            probability += 0.10
            reasons.append("disturbed soil increases annual weed pressure")
        if perennial:
            probability += 0.10
            reasons.append("perennial weeds tend to persist between seasons")

        probability = min(probability, 0.95)
        expected_coverage = min(max(latest_coverage * (1.15 if probability >= 0.6 else 0.9), 3), 90)
        density = _density_from_coverage(expected_coverage)
        risk = _risk_from_density(density, perennial)
        recommendation = _recommendation(species, density, risk, request.crop_established)

        prediction = WeedPrediction(
            prediction_run_id=prediction_run.id,
            field_id=field.id,
            species=species,
            probability=round(probability, 2),
            expected_density_class=density,
            expected_coverage_percent=round(expected_coverage, 1),
            emergence_start_date=date(request.target_year, 3, 15),
            emergence_end_date=date(request.target_year, 6, 15),
            competition_risk=risk,
            coexistence_recommendation=recommendation,
            reasoning="; ".join(reasons),
        )
        db.add(prediction)

    db.commit()
    db.refresh(prediction_run)
    return prediction_run
