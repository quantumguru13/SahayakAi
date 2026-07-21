"""Seed a provisioned Supabase project with welfare schemes (+ embeddings) and
the demonstration beneficiaries/tasks — so a Supabase-backed deploy shows a
populated dashboard immediately.

    cd backend
    python scripts/seed_supabase.py

Requires SUPABASE_URL + SUPABASE_SERVICE_KEY in backend/.env. Real OpenAI
embeddings are used when OPENAI_API_KEY is set; otherwise deterministic
pseudo-embeddings (fine for the rule-driven recommender). Idempotent: skips
tables that already contain rows.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import ai_engine  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.pii import gov_hash, mask_id  # noqa: E402
from app.core.urgency import assess_urgency  # noqa: E402
from app.data import seed  # noqa: E402
from app.models.schemas import CriticalDeadline  # noqa: E402


def _vector_literal(vec: list[float]) -> str:
    return "[" + ",".join(f"{v:.6f}" for v in vec) + "]"


def main() -> int:
    if not settings.supabase_configured:
        print("ERROR: SUPABASE_URL / SUPABASE_SERVICE_KEY not set.")
        return 1

    from supabase import create_client

    client = create_client(settings.supabase_url, settings.supabase_service_key)
    org = settings.default_org_id

    # --- Welfare schemes -----------------------------------------------------
    existing = client.table("welfare_schemes").select("id").limit(1).execute()
    if existing.data:
        print("welfare_schemes already populated — skipping.")
    else:
        for s in seed.WELFARE_SCHEMES:
            text = f"{s['title']}. {s['description']} {s['eligibility_criteria_summary']}"
            vec = ai_engine.embed_text(text)
            client.table("welfare_schemes").insert(
                {
                    "title": s["title"],
                    "description": s["description"],
                    "eligibility_criteria_summary": s["eligibility_criteria_summary"],
                    "category": s["category"],
                    "eligibility_rules": s["rules"],
                    "scheme_vector_embedding": _vector_literal(vec),
                }
            ).execute()
            print(f"  ✓ scheme: {s['title']}")

    # --- Demo beneficiaries + tasks -----------------------------------------
    existing_b = (
        client.table("beneficiaries").select("id").eq("org_id", org).limit(1).execute()
    )
    if existing_b.data:
        print("beneficiaries already populated — skipping.")
        return 0

    for b in seed.BENEFICIARIES:
        deadlines = [CriticalDeadline(**b["deadline"])] if b.get("deadline") else []
        urgency = assess_urgency(
            medical_conditions=b.get("medical_conditions", []),
            deadlines=deadlines,
            annual_income=b.get("annual_income"),
            is_disabled=b.get("is_disabled", False),
            age=b.get("age"),
        )
        client.table("beneficiaries").insert(
            {
                "id": b["id"],
                "org_id": org,
                "name": b["name"],
                "age": b.get("age"),
                "gender": b.get("gender"),
                "annual_income": b.get("annual_income"),
                "state_location": b.get("state_location"),
                "is_disabled": b.get("is_disabled", False),
                "government_id_type": b.get("government_id_type"),
                "government_id_masked": mask_id(b.get("government_id_number")),
                "government_id_hash": gov_hash(b.get("government_id_number")),
                "medical_conditions": b.get("medical_conditions", []),
                "current_priority": urgency.priority.value,
                "urgency": urgency.model_dump(),
            }
        ).execute()
        print(f"  ✓ beneficiary: {b['name']}")

    for t in seed.TASKS:
        due = t.get("due_date")
        client.table("tasks").insert(
            {
                "id": t["id"],
                "org_id": org,
                "beneficiary_id": t["beneficiary_id"],
                "title": t["title"],
                "description": t.get("description"),
                "due_date": due.isoformat() if isinstance(due, date) else None,
                "status": t["status"],
            }
        ).execute()
    print(f"  ✓ {len(seed.TASKS)} tasks")
    print("Done. Supabase is seeded.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
