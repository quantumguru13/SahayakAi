"""Beneficiary CRUD + per-case scheme matching + timeline."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.store import store
from app.models.schemas import (
    Beneficiary,
    BeneficiaryCreate,
    SchemeMatch,
    Task,
)

router = APIRouter(prefix="/beneficiaries", tags=["beneficiaries"])


@router.get("", response_model=list[Beneficiary])
def list_beneficiaries() -> list[Beneficiary]:
    return store.list_beneficiaries()


@router.post("", response_model=Beneficiary, status_code=201)
def create_beneficiary(payload: BeneficiaryCreate) -> Beneficiary:
    return store.create_beneficiary(payload)


@router.get("/{beneficiary_id}", response_model=Beneficiary)
def get_beneficiary(beneficiary_id: str) -> Beneficiary:
    ben = store.get_beneficiary(beneficiary_id)
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    return ben


@router.get("/{beneficiary_id}/schemes", response_model=list[SchemeMatch])
def get_matched_schemes(beneficiary_id: str) -> list[SchemeMatch]:
    """Query the semantic vector index for relevant welfare schemes for this case."""
    ben = store.get_beneficiary(beneficiary_id)
    if not ben:
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    return store.recommend_schemes(ben)


@router.get("/{beneficiary_id}/tasks", response_model=list[Task])
def get_tasks(beneficiary_id: str) -> list[Task]:
    if not store.get_beneficiary(beneficiary_id):
        raise HTTPException(status_code=404, detail="Beneficiary not found")
    return store.list_tasks(beneficiary_id)
