"""Deterministic Algorithmic Case Prioritization Matrix (FR-02).

Pure function — same inputs always produce the same tier + reasoning string.
Higher weight is given to imminent legal/application deadlines and to urgent
medical indicators, exactly as specified in the PRD.
"""
from __future__ import annotations

import re
from datetime import date

from app.models.schemas import (
    CriticalDeadline,
    PriorityLevel,
    UrgencyAssessment,
)

# Medical conditions that indicate life-threatening / time-critical severity.
CRITICAL_MEDICAL_KEYWORDS = {
    "cancer", "carcinoma", "tumor", "tumour", "leukemia", "leukaemia",
    "chemotherapy", "dialysis", "renal failure", "kidney failure",
    "heart failure", "cardiac", "stroke", "tuberculosis", "tb",
    "hiv", "aids", "transplant", "sepsis", "critical", "terminal",
    "malignant", "metastatic", "surgery", "emergency",
}
HIGH_MEDICAL_KEYWORDS = {
    "diabetes", "hypertension", "asthma", "anemia", "anaemia",
    "fracture", "malnutrition", "pregnancy", "disability", "epilepsy",
    "thalassemia", "hepatitis", "chronic",
}


def _kw_match(keyword: str, text: str) -> bool:
    """Whole-word / phrase match so short tokens like 'tb' or 'hiv' don't
    false-positive inside unrelated words."""
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def _days_until(d: date, today: date) -> int:
    return (d - today).days


def _score_medical(conditions: list[str]) -> tuple[int, list[str]]:
    """Return (0-100 severity, reasons)."""
    if not conditions:
        return 0, []
    score = 0
    reasons: list[str] = []
    joined = " ".join(conditions).lower()
    for kw in CRITICAL_MEDICAL_KEYWORDS:
        if _kw_match(kw, joined):
            score = max(score, 90)
            reasons.append(f"Critical medical indicator detected ('{kw}')")
            break
    if score < 90:
        for kw in HIGH_MEDICAL_KEYWORDS:
            if _kw_match(kw, joined):
                score = max(score, 55)
                reasons.append(f"Significant medical condition detected ('{kw}')")
                break
    if score == 0:
        # Some condition present but unclassified — still nonzero.
        score = 30
        reasons.append("Medical condition on record")
    return score, reasons


def _score_deadlines(
    deadlines: list[CriticalDeadline], today: date
) -> tuple[int, list[str]]:
    """Return (0-100 deadline pressure, reasons). Nearer deadlines score higher."""
    if not deadlines:
        return 0, []
    best = 0
    reasons: list[str] = []
    for dl in deadlines:
        try:
            d = date.fromisoformat(dl.date)
        except (ValueError, TypeError):
            continue
        days = _days_until(d, today)
        if days < 0:
            pressure = 100
            label = f"OVERDUE deadline: {dl.context} ({dl.date})"
        elif days <= 3:
            pressure = 95
            label = f"Deadline in {days}d: {dl.context} ({dl.date})"
        elif days <= 7:
            pressure = 80
            label = f"Deadline in {days}d: {dl.context} ({dl.date})"
        elif days <= 30:
            pressure = 55
            label = f"Deadline in {days}d: {dl.context} ({dl.date})"
        else:
            pressure = 25
            label = f"Upcoming deadline in {days}d: {dl.context} ({dl.date})"
        if pressure > best:
            best = pressure
            reasons = [label]
    return best, reasons


def assess_urgency(
    *,
    medical_conditions: list[str] | None = None,
    deadlines: list[CriticalDeadline] | None = None,
    annual_income: float | None = None,
    is_disabled: bool = False,
    age: int | None = None,
    today: date | None = None,
) -> UrgencyAssessment:
    """Deterministic urgency assessment → tier + human-readable reasoning."""
    today = today or date.today()
    medical_conditions = medical_conditions or []
    deadlines = deadlines or []

    medical_severity, medical_reasons = _score_medical(medical_conditions)
    deadline_pressure, deadline_reasons = _score_deadlines(deadlines, today)

    # Weighted blend: deadlines 55%, medical 45% (deadlines slightly favoured
    # per PRD "higher weight to upcoming legal deadlines").
    base = round(0.55 * deadline_pressure + 0.45 * medical_severity)

    reasons = list(deadline_reasons) + list(medical_reasons)
    modifiers = 0

    if is_disabled:
        modifiers += 5
        reasons.append("Registered disability status")
    if annual_income is not None and annual_income <= 150_000:
        modifiers += 5
        reasons.append("Below-poverty-line household income")
    if age is not None and (age >= 60 or age <= 12):
        modifiers += 5
        reasons.append("Vulnerable age group (senior citizen or minor)")

    score = max(0, min(100, base + modifiers))

    if score >= 80:
        priority = PriorityLevel.CRITICAL
    elif score >= 55:
        priority = PriorityLevel.HIGH
    elif score >= 30:
        priority = PriorityLevel.MEDIUM
    else:
        priority = PriorityLevel.LOW

    if not reasons:
        reasons.append("No urgent medical indicators or imminent deadlines on record")

    reasoning = f"{priority.value} — " + "; ".join(reasons[:4]) + "."

    return UrgencyAssessment(
        priority=priority,
        score=score,
        reasoning=reasoning,
        medical_severity=medical_severity,
        deadline_pressure=deadline_pressure,
    )
