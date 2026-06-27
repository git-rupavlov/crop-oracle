from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import MapWorkspace


def seed_default_workspace(db: Session) -> None:
    existing = db.scalar(select(MapWorkspace).where(MapWorkspace.name == "Park Vartopo"))
    if existing:
        return

    db.add(
        MapWorkspace(
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
    )
    db.commit()


def init_db(db: Session) -> None:
    seed_default_workspace(db)
