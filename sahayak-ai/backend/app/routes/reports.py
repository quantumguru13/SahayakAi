"""One-click Impact Report generator."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.brief import build_impact_report
from app.models.schemas import ImpactReport

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/impact", response_model=ImpactReport)
def get_impact_report() -> ImpactReport:
    return build_impact_report()
