"""Backend unit tests — confirm the extraction/urgency/matching pipeline is sound.

Run:  python -m pytest  (from the backend/ directory)
"""
from __future__ import annotations

from datetime import date, timedelta

from app.core.urgency import assess_urgency
from app.models.schemas import CriticalDeadline, PriorityLevel


def test_urgency_critical_on_cancer_and_near_deadline() -> None:
    a = assess_urgency(
        medical_conditions=["Stage II Breast Carcinoma"],
        deadlines=[
            CriticalDeadline(
                date=(date.today() + timedelta(days=2)).isoformat(),
                context="RAN grant",
            )
        ],
        annual_income=120000,
        age=62,
    )
    assert a.priority == PriorityLevel.CRITICAL
    assert a.score >= 80
    assert "CRITICAL" in a.reasoning


def test_urgency_low_when_nothing_urgent() -> None:
    a = assess_urgency(medical_conditions=[], deadlines=[], annual_income=800000, age=30)
    assert a.priority in (PriorityLevel.LOW, PriorityLevel.MEDIUM)
    assert a.score < 55


def test_urgency_is_deterministic() -> None:
    kwargs = dict(
        medical_conditions=["Renal failure"],
        deadlines=[CriticalDeadline(date="2030-01-01", context="x")],
        annual_income=90000,
        age=47,
    )
    assert assess_urgency(**kwargs).score == assess_urgency(**kwargs).score


def test_demo_extraction_matches_schema() -> None:
    """DEMO path: run_ocr_demo/extract_demo return the curated sample pair."""
    from app.core import ai_engine

    text = ai_engine.run_ocr_demo(b"medical-report-sample", "medical_report.png")
    extraction = ai_engine.extract_demo(b"medical-report-sample", "medical_report.png")
    assert text
    assert extraction.beneficiary_name
    assert extraction.detected_medical_conditions


def test_recommender_returns_eligible_schemes() -> None:
    """Seed cases are only visible in DEMO scope (LIVE shows real uploads only)."""
    from app.core.store import DataStore

    store = DataStore()
    store.set_active_mode("DEMO")
    ben = store.list_beneficiaries()[0]  # highest priority (critical medical case)
    matches = store.recommend_schemes(ben)
    assert matches, "expected at least one scheme match"
    assert 0.0 <= matches[0].confidence <= 1.0


def test_upsert_dedupes_by_government_id() -> None:
    from app.core.store import DataStore
    from app.core.urgency import assess_urgency
    from app.models.schemas import ExtractedDocument

    s = DataStore()
    before = len(s.list_beneficiaries())
    extraction = ExtractedDocument(
        beneficiary_name="Test Person",
        government_id_type="Aadhaar",
        government_id_number="1234 5678 9012",
        detected_medical_conditions=["Diabetes"],
        estimated_household_income=90000,
        age=50,
    )
    urgency = assess_urgency(medical_conditions=["Diabetes"], age=50)
    b1 = s.upsert_from_extraction(extraction, urgency)
    # Re-upload the same person (spaced differently) -> same record, not a dup.
    extraction2 = extraction.model_copy(
        update={"government_id_number": "123456789012"}
    )
    b2 = s.upsert_from_extraction(extraction2, urgency)
    assert b1.id == b2.id
    assert len(s.list_beneficiaries()) == before + 1


def test_word_boundary_keyword_matching() -> None:
    # 'tb' must not false-match inside 'outbreak-related fatigue'
    a = assess_urgency(medical_conditions=["outbreak related fatigue"])
    assert a.medical_severity < 90
    b = assess_urgency(medical_conditions=["TB (tuberculosis) confirmed"])
    assert b.medical_severity >= 90


def test_masking_helper() -> None:
    from app.core.store import _mask_id

    assert _mask_id("4821 7734 9902") == "•••• •••• 9902"
    assert _mask_id(None) is None


def test_openai_auth_failure_fallback(monkeypatch) -> None:
    from app.core import ai_engine
    from app.core.config import settings
    from openai import AuthenticationError
    import httpx

    monkeypatch.setattr(settings, "force_demo_mode", False)
    monkeypatch.setattr(settings, "openai_api_key", "sk-proj-invalidmockkey")
    monkeypatch.setattr(settings, "openai_auth_failed", False)
    # OpenAI is opt-in now (offline-first). Enable it so the failure path is reached.
    monkeypatch.setattr(settings, "use_openai", True)

    class MockEmbeddings:
        def create(self, *args, **kwargs):
            dummy_request = httpx.Request("POST", "https://api.openai.com/v1/embeddings")
            dummy_response = httpx.Response(401, request=dummy_request)
            raise AuthenticationError(
                message="Incorrect API key provided",
                response=dummy_response,
                body={"error": {"message": "Incorrect API key", "type": "invalid_request_error"}},
            )

    class MockClient:
        embeddings = MockEmbeddings()

    monkeypatch.setattr(ai_engine, "_client", lambda: MockClient())

    vec = ai_engine.embed_text("test fallback text")
    assert settings.openai_auth_failed is True
    assert settings.demo_mode is True
    assert len(vec) == 1536
    assert vec == ai_engine._pseudo_embedding("test fallback text")
