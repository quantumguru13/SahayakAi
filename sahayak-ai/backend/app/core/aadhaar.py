"""Aadhaar document intelligence — extraction, validation and verification.

Layered on top of the existing offline OCR pipeline (see ocr.py): this module
never performs OCR itself, it interprets the transcript that pipeline produced.
That keeps Aadhaar support fully offline and free of any paid API.

Privacy contract (mirrors pii.py):
  * the raw 12-digit number never leaves this module — callers receive a masked
    value ("XXXX XXXX 1234") plus a SHA-256 hash used only for dedup.
  * nothing here writes to disk.
"""
from __future__ import annotations

import hashlib
import logging
import re

from app.core.extraction import INDIAN_STATES, _clean, _to_iso_date

logger = logging.getLogger("sahayak.aadhaar")

# --------------------------------------------------------------------------- #
# Verhoeff checksum — the algorithm UIDAI uses for the 12th digit of an Aadhaar
# number. A number that is 12 digits but fails this is a transcription error or
# a fabricated card, which is exactly what we want to surface to a caseworker.
# --------------------------------------------------------------------------- #
_D_TABLE = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_P_TABLE = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def verhoeff_valid(number: str) -> bool:
    """True when `number` passes the Verhoeff checksum."""
    digits = re.sub(r"\D", "", number or "")
    if len(digits) != 12:
        return False
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _D_TABLE[c][_P_TABLE[i % 8][int(ch)]]
    return c == 0


# --------------------------------------------------------------------------- #
# Masking / hashing
# --------------------------------------------------------------------------- #
def mask_aadhaar(number: str | None) -> str | None:
    """"XXXX XXXX 1234" — the only representation allowed over the wire."""
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    if len(digits) < 4:
        return "XXXX XXXX XXXX"
    return f"XXXX XXXX {digits[-4:]}"


def redact_text(text: str | None) -> str:
    """Replace every Aadhaar-like number in free text with its masked form.

    The OCR transcript is returned to the browser and stored on the document, so
    masking only the structured field is not enough — the raw number would still
    ship inside the transcript. 16-digit VIDs are redacted the same way.
    """
    if not text:
        return text or ""

    def _sub(m: re.Match[str]) -> str:
        digits = re.sub(r"\D", "", m.group(0))
        return f"XXXX XXXX {digits[-4:]}" if len(digits) >= 4 else "XXXX XXXX XXXX"

    # 16-digit VID first, so its trailing 12 digits are not matched separately.
    text = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b", _sub, text)
    return re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", _sub, text)


def aadhaar_hash(number: str | None) -> str | None:
    """Stable hash for duplicate detection — never the raw value."""
    if not number:
        return None
    digits = re.sub(r"\D", "", number)
    return hashlib.sha256(digits.encode("utf-8")).hexdigest() if digits else None


# --------------------------------------------------------------------------- #
# Field extraction — every field is derived from the OCR transcript.
# A field that cannot be found stays None. Nothing is ever inferred or invented.
# --------------------------------------------------------------------------- #
_AADHAAR_NUM = re.compile(r"\b(\d{4}\s?\d{4}\s?\d{4})\b")
_VID_NUM = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\s?\d{4}\b")  # 16-digit VID, not Aadhaar
_PIN = re.compile(r"\b([1-9]\d{5})\b")
_MOBILE = re.compile(r"(?:mobile|phone|mob)\D{0,12}([6-9]\d{9})\b", re.IGNORECASE)
_YOB = re.compile(r"(?:year of birth|yob)\s*[:\-]?\s*(\d{4})", re.IGNORECASE)
_DOB = re.compile(
    r"(?:dob|date of birth|d\.o\.b|जन्म)\s*[:\-]?\s*"
    r"(\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}|\d{4}-\d{1,2}-\d{1,2})",
    re.IGNORECASE,
)
_GENDER = re.compile(r"\b(male|female|transgender|पुरुष|महिला)\b", re.IGNORECASE)

# Layout markers that identify a genuine UIDAI card. Used for the
# "government layout consistency" check, and to tell front from back.
# NOTE: bare "uidai" is deliberately absent — the back-of-card footer carries
# "www.uidai.gov.in" / "help@uidai.gov.in", which would misread a back capture
# as a front one and hide the fact that mandatory fields are missing.
FRONT_MARKERS = (
    "government of india",
    "unique identification authority",
    "भारत सरकार",
    "आधार",
    "aadhaar",
    "year of birth",
    "date of birth",
)
BACK_MARKERS = (
    "address",
    "help@uidai.gov.in",
    "www.uidai.gov.in",
    "1947",
    "पता",
)

_NAME_STOP = re.compile(
    r"\b(?:DOB|Date|Year|Birth|Male|Female|Gender|Aadhaar|Aadhar|VID|Government|"
    r"India|Address|Mobile|Phone|S/O|D/O|W/O|C/O)\b",
    re.IGNORECASE,
)


def _extract_name(text: str) -> str | None:
    """Aadhaar cards print the holder's name on its own line, immediately above
    the DOB/Gender line. Try labelled forms first, then that positional rule."""
    for pat in (
        r"(?:name)\s*[:\-]\s*([A-Z][A-Za-z.\s]{2,40})",
        r"(?:to|नाम)\s*[:\-]\s*([A-Z][A-Za-z.\s]{2,40})",
    ):
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            cand = _NAME_STOP.split(_clean(m.group(1)) or "")[0]
            cand = _clean(cand)
            if cand and 2 < len(cand) <= 40:
                return cand

    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    for i, ln in enumerate(lines):
        if _DOB.search(ln) or _YOB.search(ln) or _GENDER.search(ln):
            for prev in reversed(lines[max(0, i - 3) : i]):
                cand = _clean(_NAME_STOP.split(prev)[0])
                # A name line is alphabetic, title-ish and free of digits.
                if (
                    cand
                    and 2 < len(cand) <= 40
                    and not re.search(r"\d", cand)
                    and re.match(r"^[A-Za-z][A-Za-z.\s]+$", cand)
                    and not any(mk in cand.lower() for mk in FRONT_MARKERS)
                ):
                    return cand
            break
    return None


def _extract_number(text: str) -> str | None:
    """Return the 12-digit Aadhaar, ignoring 16-digit VIDs."""
    masked_text = _VID_NUM.sub(" ", text or "")
    candidates = [m.group(1) for m in _AADHAAR_NUM.finditer(masked_text)]
    # Prefer a candidate that passes Verhoeff; fall back to the first seen so a
    # mis-OCR'd number is still surfaced (and flagged) rather than dropped.
    for c in candidates:
        if verhoeff_valid(c):
            return _clean(c)
    return _clean(candidates[0]) if candidates else None


def _extract_address(text: str) -> str | None:
    m = re.search(
        r"(?:address|पता)\s*[:\-]?\s*(.{10,220})", text or "", re.IGNORECASE | re.DOTALL
    )
    if not m:
        return None
    addr = re.sub(r"\s+", " ", m.group(1))
    # Stop at the UIDAI helpline / URL block that follows the address on the back.
    addr = re.split(r"(?:www\.|help@|1947|\b\d{4}\s?\d{4}\s?\d{4}\b)", addr)[0]
    return _clean(addr)


def _extract_district(text: str, state: str | None) -> str | None:
    """District is printed before the state in the address block: '..., Kota, Rajasthan'."""
    if not state:
        return None
    m = re.search(
        r"([A-Za-z][A-Za-z\s]{2,30}?)\s*[,\-]\s*" + re.escape(state),
        text or "",
        re.IGNORECASE,
    )
    if not m:
        return None
    cand = _clean(m.group(1).split(",")[-1])
    if cand and 2 < len(cand) <= 30 and not re.search(r"\d", cand):
        return cand.title()
    return None


def _extract_state(text: str) -> str | None:
    for state in sorted(INDIAN_STATES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(state) + r"\b", text or "", re.IGNORECASE):
            return state
    return None


def read_qr(image_bytes: bytes) -> str | None:
    """Best-effort QR read using OpenCV (already a dependency — no new install).

    Aadhaar's secure QR is a signed, compressed payload; decoding it fully needs
    the UIDAI public key and spec. We surface the raw payload's presence and a
    short preview so a caseworker knows a QR was detected and readable.
    """
    try:
        import cv2
        import numpy as np

        arr = np.frombuffer(image_bytes, dtype=np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            return None
        data, _points, _straight = cv2.QRCodeDetector().detectAndDecode(img)
        return data.strip() or None
    except Exception as exc:  # noqa: BLE001 — QR is optional, never fatal
        logger.warning("QR decode failed: %s", exc)
        return None


def detect_side(text: str) -> str:
    """'front' | 'back' | 'combined' | 'unknown' from layout markers."""
    low = (text or "").lower()
    front = sum(1 for m in FRONT_MARKERS if m in low)
    back = sum(1 for m in BACK_MARKERS if m in low)
    if front and back:
        return "combined"
    if front:
        return "front"
    if back:
        return "back"
    return "unknown"


def extract(text: str, image_bytes: bytes | None = None) -> dict:
    """Parse an Aadhaar transcript into structured fields.

    Returns a plain dict (the route converts it to the Pydantic model) holding
    the RAW number — callers must mask before returning it over the wire.
    """
    text = text or ""
    number = _extract_number(text)
    dob_m = _DOB.search(text)
    dob = _to_iso_date(dob_m.group(1)) if dob_m else None
    yob_m = _YOB.search(text)
    yob = int(yob_m.group(1)) if yob_m else (int(dob[:4]) if dob else None)

    gender = None
    g = _GENDER.search(text)
    if g:
        raw = g.group(1).lower()
        gender = {"पुरुष": "Male", "महिला": "Female"}.get(raw, raw.capitalize())

    state = _extract_state(text)
    pin_m = _PIN.search(text)
    mobile_m = _MOBILE.search(text)

    return {
        "full_name": _extract_name(text),
        "aadhaar_number": number,          # RAW — mask before serialising
        "date_of_birth": dob,
        "year_of_birth": yob,
        "gender": gender,
        "address": _extract_address(text),
        "state": state,
        "district": _extract_district(text, state),
        "pin_code": pin_m.group(1) if pin_m else None,
        "mobile": mobile_m.group(1) if mobile_m else None,
        "qr_payload": read_qr(image_bytes) if image_bytes else None,
        "side": detect_side(text),
    }


# --------------------------------------------------------------------------- #
# Verification
# --------------------------------------------------------------------------- #
MANDATORY_FIELDS = ("full_name", "aadhaar_number", "gender")
# Below this OCR confidence we never assert "verified" — we ask for a human.
MIN_OCR_CONFIDENCE = 0.55


def verify(fields: dict, ocr_confidence: float) -> dict:
    """Run every Aadhaar check and return a verification summary.

    Deliberately never returns a hard "invalid" for a readable card: an NGO
    caseworker needs "look at this yourself", not a dead end. The worst outcome
    is MANUAL_REVIEW with the specific reasons attached.
    """
    number = fields.get("aadhaar_number") or ""
    digits = re.sub(r"\D", "", number)
    checks: dict[str, bool] = {}
    reasons: list[str] = []

    checks["number_present"] = bool(digits)
    if not digits:
        reasons.append("No Aadhaar number found in the document.")

    checks["length_12"] = len(digits) == 12
    if digits and len(digits) != 12:
        reasons.append(f"Aadhaar number has {len(digits)} digits, expected 12.")

    checks["numeric_only"] = bool(digits) and digits.isdigit()

    checks["checksum_valid"] = verhoeff_valid(digits) if digits else False
    if digits and len(digits) == 12 and not checks["checksum_valid"]:
        reasons.append("Aadhaar checksum failed — likely an OCR misread of a digit.")

    # UIDAI never issues a number starting 0 or 1.
    checks["valid_prefix"] = bool(digits) and digits[0] not in ("0", "1")
    if digits and not checks["valid_prefix"]:
        reasons.append("Aadhaar numbers cannot begin with 0 or 1.")

    checks["ocr_confidence_ok"] = ocr_confidence >= MIN_OCR_CONFIDENCE
    if not checks["ocr_confidence_ok"]:
        reasons.append(
            f"OCR confidence {ocr_confidence:.0%} is below "
            f"{MIN_OCR_CONFIDENCE:.0%} — text may be misread."
        )

    side = fields.get("side", "unknown")
    checks["layout_consistent"] = side in ("front", "back", "combined")
    if not checks["layout_consistent"]:
        reasons.append(
            "Document does not carry recognisable Aadhaar layout markers."
        )

    missing = [f for f in MANDATORY_FIELDS if not fields.get(f)]
    checks["mandatory_fields_present"] = not missing
    if missing:
        reasons.append(
            "Missing mandatory field(s): "
            + ", ".join(f.replace("_", " ") for f in missing)
        )

    if all(checks.values()):
        status = "VERIFIED"
    elif not checks["number_present"] and side == "unknown":
        status = "NOT_AADHAAR"
        reasons.insert(0, "This does not appear to be an Aadhaar document.")
    else:
        status = "MANUAL_REVIEW"

    return {
        "status": status,
        "checks": checks,
        "reasons": reasons,
        "missing_fields": missing,
        "manual_review": status != "VERIFIED",
        "side": side,
    }


def merge_sides(front: dict, back: dict) -> tuple[dict, list[str]]:
    """Combine a front and a back capture into one record.

    Returns (merged_fields, conflicts). A conflict means the two images disagree
    on a field that should match — a strong signal the pair is mismatched.
    """
    merged = dict(front)
    conflicts: list[str] = []
    for key, value in back.items():
        if value in (None, "", "unknown"):
            continue
        current = merged.get(key)
        if current in (None, "", "unknown"):
            merged[key] = value
        elif key in ("aadhaar_number", "date_of_birth", "gender") and current != value:
            conflicts.append(
                f"{key.replace('_', ' ')} differs between front and back"
            )
    merged["side"] = "combined"
    return merged, conflicts
