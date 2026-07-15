"""FastAPI-app: lifespan, statiska filer och router-registrering."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routes import web
from app.services.konfig_service import ladda_konfig_till_minne

STATIC_DIR = Path(__file__).resolve().parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    ladda_konfig_till_minne()   # DB-konfig -> namnnormalisering
    yield


app = FastAPI(title="Håven - kollektverktyg", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.include_router(web.router)
