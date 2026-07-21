"""Generate real 1536-dim embeddings for welfare schemes and write them to Supabase.

Only needed for LIVE mode with a provisioned Supabase project. Run after
supabase/seed.sql has inserted the scheme rows.

    cd backend
    python scripts/seed_embeddings.py

Requires OPENAI_API_KEY, SUPABASE_URL and SUPABASE_SERVICE_KEY in backend/.env.
Uses only httpx + openai (already in requirements.txt) — no extra dependencies.
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

# Make `app` importable when run from the backend/ directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core import ai_engine  # noqa: E402


def main() -> int:
    if not settings.openai_configured:
        print("ERROR: OPENAI_API_KEY not set — cannot generate real embeddings.")
        return 1
    if not settings.supabase_configured:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_KEY not set.")
        return 1

    base = settings.supabase_url.rstrip("/")
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{base}/rest/v1/welfare_schemes",
            params={"select": "id,title,description,eligibility_criteria_summary"},
            headers=headers,
        )
        resp.raise_for_status()
        schemes = resp.json()
        print(f"Found {len(schemes)} welfare schemes to embed.")

        for s in schemes:
            text = (
                f"{s['title']}. {s['description']} "
                f"{s.get('eligibility_criteria_summary') or ''}"
            )
            vector = ai_engine.embed_text(text)  # real embedding in live mode
            vector_literal = "[" + ",".join(f"{v:.6f}" for v in vector) + "]"
            patch = client.patch(
                f"{base}/rest/v1/welfare_schemes",
                params={"id": f"eq.{s['id']}"},
                headers=headers,
                json={"scheme_vector_embedding": vector_literal},
            )
            patch.raise_for_status()
            print(f"  ✓ embedded: {s['title']}")

    print("Done. All welfare schemes now have 1536-dim embeddings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
