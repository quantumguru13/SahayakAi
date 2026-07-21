"""Offline AI information extraction — raw OCR text -> structured JSON.

This is the LIVE-mode extractor used when no OpenAI key is present. It is a
deterministic rule/regex engine (no network, no mock data): every field is derived
*from the OCR text of the uploaded document*, so two different documents always
produce two different structured results.

When an OpenAI key IS configured, ``ai_engine`` uses GPT-4o for extraction instead;
this module is the always-available offline path and the automatic fallback.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.models.schemas import CriticalDeadline, ExtractedDocument

# --------------------------------------------------------------------------- #
# Reference data
# --------------------------------------------------------------------------- #
INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram",
    "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Delhi", "Jammu and Kashmir", "Ladakh", "Puducherry", "Chandigarh",
]

# Medical findings — surface condition/lab keywords verbatim from the text.
MEDICAL_KEYWORDS = [
    "carcinoma", "cancer", "malignant", "tumor", "tumour", "chemotherapy",
    "dialysis", "renal failure", "kidney disease", "ckd", "cardiac", "heart failure",
    "diabetes", "diabetic", "hypertension", "anemia", "anaemia", "thalassemia",
    "tuberculosis", "leukemia", "stroke", "paralysis", "fracture", "hepatitis",
    "cirrhosis", "hiv", "aids", "asthma", "pneumonia", "sepsis", "surgery",
    "transplant", "biopsy", "metastasis", "locomotor disability", "blindness",
]

DISABILITY_HINTS = [
    "disability", "disabled", "pwd", "handicap", "locomotor", "blind",
    "deaf", "physically challenged", "divyang",
]

# Death of the primary breadwinner / widowhood — the triggering life event for
# the National Family Benefit Scheme. Indian certificates express this as
# "W/o Late Shri ...", "widow", "deceased husband", etc.
BEREAVEMENT_HINTS = [
    "widow", "widowed", "late shri", "late smt", "deceased", "death of",
    "expired on", "breadwinner", "w/o late", "s/o late", "d/o late",
]

# Occupation signals — drive livelihood-linked schemes (e.g. PM-KISAN for farmers).
# Ordered most-specific first so "agricultural labourer" reads as farmer, not labourer.
OCCUPATION_HINTS: list[tuple[str, list[str]]] = [
    ("Farmer", ["farmer", "kisan", "agricultur", "cultivator", "krishi", "landholding"]),
    ("Student", ["student", "scholarship", "class ", "college", "school going"]),
    ("Daily wage labourer", ["daily-wage", "daily wage", "labourer", "laborer", "construction worker"]),
    ("Domestic worker", ["domestic worker", "housemaid", "domestic help"]),
    ("Weaver", ["weaver", "handloom"]),
    ("Fisherman", ["fisherman", "fisherfolk", "matsya"]),
]

# Deadline trigger phrases — a date near one of these becomes a critical deadline.
DEADLINE_TRIGGERS = [
    "last date", "before", "due by", "due date", "deadline", "submit by",
    "apply by", "valid till", "expiry", "renewal", "must be submitted",
    "to be submitted", "closing date",
]

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7,
    "aug": 8, "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}


@dataclass
class ExtractionResult:
    document: ExtractedDocument
    confidence: float          # 0-1, share of key fields confidently found
    fields_found: list[str]
    dob: str | None = None     # surfaced for the debug panel / UI
    address: str | None = None


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _clean(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"\s+", " ", s).strip(" :;-|.\t")
    return s or None


def _to_iso_date(raw: str) -> str | None:
    """Normalize dd/mm/yyyy, dd-mm-yyyy, '5 Jan 2026', 'Jan 5 2026', yyyy-mm-dd."""
    raw = raw.strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})$", raw)
    if m:
        y, mo, d = map(int, m.groups())
        return _safe_iso(y, mo, d)
    m = re.match(r"^(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})$", raw)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        return _safe_iso(y, mo, d)
    m = re.match(r"^(\d{1,2})\s+([A-Za-z]{3,9})\.?\s+(\d{4})$", raw)
    if m:
        d, mon, y = int(m.group(1)), m.group(2)[:3].lower(), int(m.group(3))
        if mon in _MONTHS:
            return _safe_iso(y, _MONTHS[mon], d)
    m = re.match(r"^([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})$", raw)
    if m:
        mon, d, y = m.group(1)[:3].lower(), int(m.group(2)), int(m.group(3))
        if mon in _MONTHS:
            return _safe_iso(y, _MONTHS[mon], d)
    return None


def _safe_iso(y: int, mo: int, d: int) -> str | None:
    if 1 <= mo <= 12 and 1 <= d <= 31 and 1900 <= y <= 2100:
        return f"{y:04d}-{mo:02d}-{d:02d}"
    return None


_DATE_PATTERN = re.compile(
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
    r"|\d{4}-\d{1,2}-\d{1,2}"
    r"|\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4}"
    r"|[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4})"
)


# --------------------------------------------------------------------------- #
# Field extractors
# --------------------------------------------------------------------------- #
def _extract_name(text: str) -> str | None:
    patterns = [
        r"(?:patient\s*name|beneficiary\s*name|applicant\s*name)\s*[:\-]\s*([A-Z][A-Za-z.\s]{2,40})",
        r"(?:name of (?:the )?(?:patient|beneficiary|applicant))\s*[:\-]\s*([A-Z][A-Za-z.\s]{2,40})",
        r"\bname\s*[:\-]\s*([A-Z][A-Za-z.\s]{2,40})",
        r"(?:this is to certify that|certify that)\s*(?:smt\.?|shri\.?|mr\.?|mrs\.?|ms\.?)?\s*([A-Z][A-Za-z.\s]{2,40})",
        r"\bpatient\s*[:\-]\s*([A-Z][A-Za-z.\s]{2,40})",
    ]
    # Label tokens that, if captured after the name, mark where the name ends.
    stop = (
        r"\b(?:Age|DOB|Date|Gender|Sex|Aadhaar|Aadhar|UID|PAN|Voter|EPIC|Ration|"
        r"Address|State|Annual|Income|Salary|Diagnosis|Advised|W/o|S/o|D/o|Age/Sex)\b"
    )
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            cand = _clean(m.group(1))
            if not cand:
                continue
            # Trim at a trailing label token or a big gap (column break).
            cand = re.split(r"\s{2,}|" + stop, cand, flags=re.IGNORECASE)[0]
            # Drop a dangling single letter: the name capture stops at the "/" in
            # relational suffixes, leaving "Sunita Meena W" from "W/o Late Shri ...".
            cand = re.sub(r"\s+[A-Za-z]\.?\s*$", "", cand or "")
            cand = _clean(cand)
            if cand and 2 < len(cand) <= 40:
                return cand if not cand.islower() else cand.title()
    return None


def _extract_dob(text: str) -> str | None:
    m = re.search(r"(?:dob|date of birth|d\.o\.b)\s*[:\-]?\s*" + _DATE_PATTERN.pattern, text, re.IGNORECASE)
    if m:
        return _to_iso_date(m.group(1))
    return None


def _extract_age(text: str) -> int | None:
    for pat in [
        r"\bage\s*(?:/\s*sex)?\s*[:\-]\s*(\d{1,3})",
        r"\bage\s*[:\-]?\s*(\d{1,3})\s*(?:years|yrs|/)",
        r"(\d{1,3})\s*(?:years|yrs)\s*old",
    ]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            age = int(m.group(1))
            if 0 < age < 120:
                return age
    return None


def _extract_gender(text: str) -> str | None:
    m = re.search(r"(?:gender|sex)\s*[:\-]?\s*(male|female|other|m|f)\b", text, re.IGNORECASE)
    if m:
        g = m.group(1).lower()
        return {"m": "Male", "f": "Female"}.get(g, g.capitalize())
    if re.search(r"\bfemale\b", text, re.IGNORECASE):
        return "Female"
    if re.search(r"\bmale\b", text, re.IGNORECASE):
        return "Male"
    return None


def _extract_state(text: str) -> str | None:
    for state in sorted(INDIAN_STATES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(state) + r"\b", text, re.IGNORECASE):
            return state
    return None


def _extract_address(text: str) -> str | None:
    m = re.search(r"address\s*[:\-]\s*([^\n]{3,80})", text, re.IGNORECASE)
    if m:
        return _clean(m.group(1))
    # Fall back to the state if we found one (better than nothing).
    return _extract_state(text)


def _extract_gov_id(text: str) -> tuple[str | None, str | None]:
    """Return (id_type, id_number)."""
    sep = r"[\s:.\-]*"  # label/value separator that never eats letters or digits
    # Aadhaar — 12 digits, usually grouped 4-4-4.
    m = re.search(r"(?:aadhaar|aadhar|uid)" + sep + r"(\d{4}\s?\d{4}\s?\d{4})", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b(\d{4}\s\d{4}\s\d{4})\b", text)
    if m:
        return "Aadhaar", _clean(m.group(1))
    # PAN — 5 letters, 4 digits, 1 letter.
    m = re.search(r"(?:pan)" + sep + r"([A-Z]{5}\d{4}[A-Z])", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b([A-Z]{5}\d{4}[A-Z])\b", text)
    if m:
        return "PAN", m.group(1).upper()
    # Voter ID — 2-3 letters + 7-8 digits (EPIC).
    m = re.search(r"(?:voter\s*id|epic)" + sep + r"([A-Z]{2,3}\d{6,8})", text, re.IGNORECASE)
    if not m:
        m = re.search(r"\b([A-Z]{3}\d{7})\b", text)
    if m:
        return "Voter ID", m.group(1).upper()
    # Ration card — free-form alphanumeric after the label.
    m = re.search(r"ration\s*card" + sep + r"([A-Z0-9\-]{5,20})", text, re.IGNORECASE)
    if m:
        return "Ration Card", m.group(1).upper()
    return None, None


def _extract_income(text: str) -> float | None:
    # Prefer an income explicitly labelled; else any Rs. amount.
    labelled = re.search(
        r"(?:income|salary|earning)[^\n]{0,40}?(?:rs\.?|inr|₹)\s*([\d,]+)",
        text, re.IGNORECASE,
    )
    m = labelled or re.search(r"(?:rs\.?|inr|₹)\s*([\d,]{3,})", text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return None
    return None


def _extract_medical(text: str) -> list[str]:
    low = text.lower()
    found: list[str] = []
    for kw in MEDICAL_KEYWORDS:
        if kw in low:
            # Surface the surrounding phrase (up to a few words) for context.
            m = re.search(r"([A-Za-z][A-Za-z0-9 ,()\-]*\b" + re.escape(kw) + r"\b[A-Za-z0-9 ()\-]*)", text, re.IGNORECASE)
            phrase = _clean(m.group(1)) if m else kw.title()
            phrase = phrase or kw.title()
            # Drop trailing noise: dates, "by/before ...", stray numbers.
            trimmed = re.split(r"\b(?:by|before|due|apply|submit|fund|on)\b", phrase, flags=re.IGNORECASE)[0]
            trimmed = re.sub(r"\b\d{1,4}\b\s*$", "", trimmed).strip(" ,-")
            trimmed = _clean(trimmed)
            # Keep the trimmed phrase only if it still names the condition; else use
            # the keyword itself (avoids leftover fragments like "URGENT").
            phrase = trimmed if (trimmed and kw in trimmed.lower()) else kw.title()
            phrase = phrase[:60]
            # De-dup case-insensitively.
            if phrase and phrase.lower() not in {f.lower() for f in found}:
                found.append(phrase)
    return found[:8]


def _extract_deadlines(text: str) -> list[CriticalDeadline]:
    deadlines: list[CriticalDeadline] = []
    seen: set[str] = set()
    # Work line-by-line + full text so triggers and dates on the same line pair up.
    for chunk in re.split(r"[\n.]", text):
        low = chunk.lower()
        if not any(t in low for t in DEADLINE_TRIGGERS):
            continue
        dm = _DATE_PATTERN.search(chunk)
        if not dm:
            continue
        iso = _to_iso_date(dm.group(1))
        if not iso or iso in seen:
            continue
        seen.add(iso)
        context = _clean(re.sub(_DATE_PATTERN, "", chunk)) or "Application deadline"
        # Strip trailing connective words left dangling after removing the date
        # (e.g. "...health scheme is" -> "...health scheme") for tidy task titles.
        context = re.sub(
            r"\s+(?:is|on|before|by|due|to|the|of|for|:|-)+\s*$", "", context,
            flags=re.IGNORECASE,
        ).strip(" :;-,")
        context = context or "Application deadline"
        deadlines.append(CriticalDeadline(date=iso, context=context[:80]))
    return deadlines[:5]


def _is_disabled(text: str) -> bool:
    low = text.lower()
    return any(h in low for h in DISABILITY_HINTS)


def _is_bereaved(text: str) -> bool:
    low = text.lower()
    return any(h in low for h in BEREAVEMENT_HINTS)


def _extract_occupation(text: str) -> str | None:
    low = (text or "").lower()
    for label, hints in OCCUPATION_HINTS:
        if any(h in low for h in hints):
            return label
    return None


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def extract_from_text(ocr_text: str) -> ExtractionResult:
    """Deterministically parse OCR text into an ``ExtractedDocument``.

    Confidence is the share of the primary fields we could locate — a genuine
    signal the UI can display, not a hardcoded number.
    """
    text = ocr_text or ""
    name = _extract_name(text)
    dob = _extract_dob(text)
    age = _extract_age(text)
    if age is None and dob:
        try:
            from datetime import date
            y = int(dob[:4])
            age = max(0, date.today().year - y)
        except Exception:  # noqa: BLE001
            age = None
    gender = _extract_gender(text)
    state = _extract_state(text)
    address = _extract_address(text)
    gid_type, gid_num = _extract_gov_id(text)
    income = _extract_income(text)
    medical = _extract_medical(text)
    deadlines = _extract_deadlines(text)
    disabled = _is_disabled(text)
    bereaved = _is_bereaved(text)
    occupation = _extract_occupation(text)

    document = ExtractedDocument(
        beneficiary_name=name,
        government_id_type=gid_type,
        government_id_number=gid_num,
        critical_deadlines=deadlines,
        detected_medical_conditions=medical,
        estimated_household_income=income,
        age=age,
        gender=gender,
        state_location=state,
        is_disabled=disabled,
        is_bereaved=bereaved,
        occupation=occupation,
        dob=dob,
        address=address,
    )

    # Confidence: fraction of the "core" fields we located.
    core = {
        "name": bool(name),
        "gov_id": bool(gid_num),
        "income_or_medical": bool(income) or bool(medical),
        "location": bool(state or address),
        "date_or_age": bool(deadlines or dob or age),
    }
    fields_found = [k for k, v in core.items() if v]
    confidence = round(len(fields_found) / len(core), 4)

    return ExtractionResult(
        document=document,
        confidence=confidence,
        fields_found=fields_found,
        dob=dob,
        address=address,
    )
