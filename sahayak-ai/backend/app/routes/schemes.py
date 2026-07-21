"""Welfare scheme catalogue endpoint."""
from __future__ import annotations

from fastapi import APIRouter

from app.core.store import store
from app.models.schemas import WelfareScheme

router = APIRouter(prefix="/schemes", tags=["schemes"])


@router.get("", response_model=list[WelfareScheme])
def list_schemes() -> list[WelfareScheme]:
    return store.list_schemes()
