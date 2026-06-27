from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI

from app.api.fields import router as fields_router
from app.api.map import router as map_router
from app.db.init_db import init_db
from app.db.session import Base, SessionLocal, engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        init_db(db)
    yield


app = FastAPI(title="Crop Oracle API", version="0.1.0", lifespan=lifespan)
app.include_router(fields_router)
app.include_router(map_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
