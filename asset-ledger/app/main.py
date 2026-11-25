import os
from contextlib import asynccontextmanager

import app.formtext  # noqa: F401  表单里的中文按 UTF-8 还原

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.cluster import assert_cluster_exclusive
from app.db import Base, engine
from app.migrate import apply_migrations
from app.models import ensure_indexes
from app.routes import router
from app.services import translate_integrity


def boot() -> None:
    assert_cluster_exclusive()
    Base.metadata.create_all(engine)
    ensure_indexes(engine)
    apply_migrations(engine)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    boot()
    yield


app = FastAPI(title="机房/办公资产录入台账", lifespan=lifespan)
app.include_router(router)


@app.exception_handler(IntegrityError)
async def integrity_error(_request, exc: IntegrityError):
    return PlainTextResponse(translate_integrity(exc), status_code=400)


@app.get("/healthz")
def healthz():
    with engine.connect() as conn:
        conn.execute(text("select 1"))
    return PlainTextResponse("ok")


app.mount("/static", StaticFiles(directory=str(os.path.join(os.path.dirname(__file__), "static"))), name="static")
