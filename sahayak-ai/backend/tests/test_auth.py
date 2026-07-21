"""Auth tests — demo bypass vs. enforced JWT.

Run:  python -m pytest tests/test_auth.py
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.core import auth as authmod
from app.main import app

client = TestClient(app)


def test_auth_config_reports_disabled_in_demo() -> None:
    r = client.get("/api/v1/auth/config")
    assert r.status_code == 200
    assert r.json()["auth_enabled"] is False


def test_me_returns_demo_user_when_auth_disabled() -> None:
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["is_demo"] is True
    assert body["org_id"] == "default-org"


def test_protected_route_open_when_auth_disabled() -> None:
    # No Authorization header, yet the demo bypass allows access.
    r = client.get("/api/v1/dashboard/metrics")
    assert r.status_code == 200


def test_protected_route_401_when_auth_enabled_without_token(monkeypatch) -> None:
    # Simulate a configured Supabase project (turns auth on).
    monkeypatch.setattr(authmod.settings, "supabase_url", "https://demo.supabase.co")
    monkeypatch.setattr(authmod.settings, "force_demo_mode", False)
    monkeypatch.setattr(authmod.settings, "force_disable_auth", False)
    assert authmod.settings.auth_enabled is True

    r = client.get("/api/v1/dashboard/metrics")
    assert r.status_code == 401

    r2 = client.get(
        "/api/v1/dashboard/metrics",
        headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert r2.status_code == 401
