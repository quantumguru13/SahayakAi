"""Dashboard + AI Daily Brief endpoints."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.brief import build_daily_brief
from app.core.store import store
from app.models.schemas import DailyBrief, DashboardMetrics, PipelineMode

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class ModeRequest(BaseModel):
    mode: PipelineMode


@router.get("/mode")
def get_mode() -> dict[str, str]:
    return {"active_mode": store.active_mode}


@router.post("/mode")
def set_mode(payload: ModeRequest) -> dict[str, str]:
    """Scope the dashboard/lists to LIVE (real uploads only) or DEMO (sample data)."""
    active = store.set_active_mode(payload.mode.value)
    return {"active_mode": active}


@router.get("/brief", response_model=DailyBrief)
def get_daily_brief() -> DailyBrief:
    """Consolidated metrics view + compiled daily AI status summary."""
    return build_daily_brief()


@router.get("/metrics", response_model=DashboardMetrics)
def get_metrics() -> DashboardMetrics:
    return store.metrics()


@router.post("/reset")
def reset_demo() -> dict[str, str]:
    """Resets the demo data store back to the seeded default state."""
    store.reset()
    return {"status": "ok", "message": "Demo data reset successfully"}
