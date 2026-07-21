"""Sahayak AI — FastAPI application entrypoint.

AI-native Humanitarian Case Intelligence Platform.
Run:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.store import store
from app.models.schemas import HealthResponse
from app.routes import (
    auth,
    beneficiaries,
    dashboard,
    documents,
    reports,
    schemes,
    tasks,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sahayak")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.core.store import store

    mode = "DEMO (deterministic mock AI)" if settings.demo_mode else "LIVE (OpenAI)"
    logger.info("Sahayak AI starting — mode=%s", mode)
    logger.info(
        "OpenAI=%s | Supabase=%s | Auth=%s | Store=%s",
        settings.openai_configured,
        settings.supabase_configured,
        settings.auth_enabled,
        type(store).__name__,
    )
    yield


app = FastAPI(
    title="Sahayak AI",
    description="AI-native Humanitarian Case Intelligence Platform",
    version="1.0.0-MVP",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# `auth` is mounted without the guard (its own endpoints resolve the user).
app.include_router(auth.router, prefix=settings.api_v1_prefix)

# All data routers require a valid session when auth is enabled (demo bypasses).
_guard = [Depends(get_current_user)]
for r in (dashboard, beneficiaries, documents, tasks, schemes, reports):
    app.include_router(r.router, prefix=settings.api_v1_prefix, dependencies=_guard)


@app.get("/", tags=["health"])
def root() -> dict:
    return {"service": "Sahayak AI", "docs": "/docs", "health": "/health"}


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health() -> HealthResponse:
    from app.models.schemas import PipelineMode

    return HealthResponse(
        status="ok",
        demo_mode=settings.demo_mode,
        openai_configured=settings.openai_configured,
        supabase_configured=settings.supabase_configured,
        auth_enabled=settings.auth_enabled,
        default_mode=PipelineMode(settings.default_pipeline_mode),
        live_ocr_available=settings.live_ocr_available,
        ocr_engines=settings.live_ocr_engines(),
        active_mode=PipelineMode(store.active_mode),
    )
