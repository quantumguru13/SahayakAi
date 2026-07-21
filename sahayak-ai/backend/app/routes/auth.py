"""Auth endpoints — surface the current session identity to the frontend."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/me", response_model=CurrentUser)
def me(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Return the authenticated user (or the demo user when auth is disabled)."""
    return user


@router.get("/config")
def auth_config() -> dict:
    """Public: lets the frontend know whether to show the login gate."""
    return {"auth_enabled": settings.auth_enabled}
