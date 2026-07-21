"""Authentication — Supabase JWT verification (FastAPI dependency).

Behaviour:
  * auth disabled (no Supabase / demo)  -> returns a DEMO_USER, never 401.
  * auth enabled                        -> requires a valid Supabase bearer token,
                                           verified against the project JWKS
                                           (asymmetric ES256/RS256) or, as a
                                           fallback, the legacy HS256 shared secret.

This keeps the offline judge demo working with zero credentials while enforcing
real authentication the moment a Supabase project is configured.
"""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from fastapi import HTTPException, Request, status
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("sahayak.auth")


class CurrentUser(BaseModel):
    id: str
    email: Optional[str] = None
    org_id: str = "default-org"
    role: str = "authenticated"
    is_demo: bool = False


# Shared identity used when auth is disabled (keeps the demo single-tenant).
DEMO_USER = CurrentUser(
    id="demo-user",
    email="demo@sahayak.ai",
    org_id="default-org",
    role="authenticated",
    is_demo=True,
)


@lru_cache
def _jwk_client():
    import jwt  # PyJWT

    return jwt.PyJWKClient(settings.jwks_url)


def _bearer_token(request: Request) -> Optional[str]:
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip() or None
    return None


def _decode(token: str) -> dict:
    import jwt

    common = dict(
        audience=settings.supabase_jwt_aud,
        options={"verify_aud": True, "verify_exp": True},
    )
    if settings.jwks_url:
        signing_key = _jwk_client().get_signing_key_from_jwt(token).key
        return jwt.decode(
            token, signing_key, algorithms=["ES256", "RS256"], **common
        )
    if settings.supabase_jwt_secret:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            **common,
        )
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Auth is enabled but no JWKS URL or JWT secret is configured.",
    )


def get_current_user(request: Request) -> CurrentUser:
    """FastAPI dependency — resolves the authenticated user (or the demo user)."""
    if not settings.auth_enabled:
        return DEMO_USER

    token = _bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = _decode(token)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 — surface any verification failure as 401
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    app_metadata = payload.get("app_metadata") or {}
    org_id = app_metadata.get("org_id") or payload.get("org_id") or "default-org"
    return CurrentUser(
        id=str(payload.get("sub", "")),
        email=payload.get("email"),
        org_id=str(org_id),
        role=str(payload.get("role", "authenticated")),
        is_demo=False,
    )
