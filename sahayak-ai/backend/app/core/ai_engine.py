"""AI engine — OCR text extraction, GPT-4o structured JSON extraction, embeddings.

Two execution paths behind one interface:
  * LIVE  — uses OpenAI (gpt-4o vision for OCR + extraction, text-embedding-3-small).
  * DEMO  — deterministic, zero-network mock returning curated realistic results.

The switch is automatic (see config.settings.demo_mode).
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import math
import struct
from functools import lru_cache

from app.core.config import settings
from app.data.samples import match_sample_by_filename, pick_sample
from app.models.schemas import ExtractedDocument

logger = logging.getLogger("sahayak.ai")

EMBEDDING_DIM = 1536

SYSTEM_PROMPT = (
    "You are an expert data parsing agent specializing in Indian NGO document "
    "auditing.\n"
    "TASK: Analyze the provided raw OCR text transcript and extract key structural "
    "properties.\n"
    "OUTPUT FORMAT: Return a valid JSON object matching this exact schema. Do not "
    "include markdown wraps like ```json.\n\n"
    "Required JSON Structure:\n"
    "{\n"
    '  "beneficiary_name": String or null,\n'
    '  "government_id_type": "Aadhaar" | "PAN" | "Ration Card" | "Voter ID" | null,\n'
    '  "government_id_number": String or null,\n'
    '  "critical_deadlines": [{"date": "YYYY-MM-DD", "context": String}],\n'
    '  "detected_medical_conditions": [String],\n'
    '  "estimated_household_income": Number or null,\n'
    '  "age": Number or null,\n'
    '  "gender": "Male" | "Female" | "Other" | null,\n'
    '  "state_location": String (Indian state) or null,\n'
    '  "is_disabled": true | false\n'
    "}"
)


# --------------------------------------------------------------------------- #
# OpenAI client (lazy — never imported/instantiated in demo mode)
# --------------------------------------------------------------------------- #
@lru_cache
def _client():
    from openai import OpenAI  # local import keeps demo mode dependency-free

    return OpenAI(api_key=settings.openai_api_key)


def _handle_openai_error(exc: Exception) -> None:
    from openai import OpenAIError
    if isinstance(exc, OpenAIError):
        from openai import APIConnectionError, AuthenticationError
        if isinstance(exc, AuthenticationError):
            err_type = "OpenAI Authentication Error (invalid/expired API key)"
        elif isinstance(exc, APIConnectionError):
            err_type = "OpenAI API Connection Error (network offline)"
        else:
            err_type = f"OpenAI API Error ({type(exc).__name__})"
        logger.warning(
            "%s: %s. Falling back to Demo Mode.",
            err_type,
            exc,
        )
    else:
        logger.warning(
            "Unexpected error during OpenAI call: %s. Falling back to Demo Mode.",
            exc,
        )
    settings.openai_auth_failed = True


def _seed_from_bytes(content: bytes, filename: str) -> int:
    h = hashlib.sha256(content + filename.encode("utf-8", "ignore")).hexdigest()
    return int(h[:8], 16)


# --------------------------------------------------------------------------- #
# Stage 1: OCR — two explicit, non-overlapping paths.
#   * LIVE — real OCR on the uploaded bytes (never samples).  raises on failure.
#   * DEMO — deterministic curated sample (no OCR, no network).
# The caller (routes/documents.py) chooses which to run based on the request mode.
# --------------------------------------------------------------------------- #
def _pick_sample(content: bytes, filename: str) -> dict:
    return match_sample_by_filename(filename) or pick_sample(
        _seed_from_bytes(content, filename)
    )


def run_ocr_demo(content: bytes, filename: str) -> str:
    """DEMO mode: return a curated sample transcript. Never touches OCR/network."""
    return _pick_sample(content, filename)["ocr_text"]


def run_ocr_live(content: bytes, filename: str, content_type: str | None):
    """LIVE mode: transcribe the real uploaded document.

    Returns an ``ocr.OcrResult``. Raises ``ocr.OcrUnavailableError`` if no engine
    can read the file — the route turns that into the graceful fallback response.
    """
    from app.core import ocr

    return ocr.run_pipeline(
        content,
        filename,
        content_type,
        # Offline-first: GPT-4o Vision is used only when explicitly opted into.
        allow_openai=settings.use_openai and settings.openai_configured,
        openai_api_key=settings.openai_api_key,
        openai_chat_model=settings.openai_chat_model,
        # A 401/connection failure flips settings.openai_auth_failed, so from the
        # next request on we stop offering GPT-4o and go straight to EasyOCR /
        # Tesseract (and to DEMO if neither is installed).
        on_openai_error=_handle_openai_error,
    )


# --------------------------------------------------------------------------- #
# Stage 2: Structured extraction — OCR text -> strict JSON.
#   * DEMO — curated ground-truth extraction paired with the sample.
#   * LIVE — GPT-4o JSON extraction if a key exists, else the deterministic
#            rule-based extractor (extraction.py). Always derived from OCR text.
# --------------------------------------------------------------------------- #
def extract_demo(content: bytes, filename: str) -> ExtractedDocument:
    sample = _pick_sample(content, filename)
    data = dict(sample["extraction"])
    prof = sample.get("profile", {})
    for key in (
        "age", "gender", "state_location", "is_disabled", "is_bereaved", "occupation",
    ):
        # Only copy keys the sample actually defines. Injecting a None would fail
        # validation for the non-optional booleans (is_disabled / is_bereaved).
        if prof.get(key) is not None:
            data.setdefault(key, prof[key])
    return ExtractedDocument.model_validate(data)


def extract_live(ocr_text: str) -> tuple[ExtractedDocument, float, str]:
    """Return ``(document, extraction_confidence, ai_status)``.

    ai_status: 'ok' = intended engine succeeded; 'fallback' = GPT-4o failed and we
    used the offline rule-based extractor instead.

    Offline by default: the deterministic rule extractor (extraction.py) reads the
    real OCR text. GPT-4o is used only when USE_OPENAI=true. Either path derives
    every field from the uploaded document — neither can return sample data.
    """
    if settings.use_openai and settings.openai_configured:
        try:
            resp = _client().chat.completions.create(
                model=settings.openai_chat_model,
                temperature=settings.openai_temperature,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"OCR TEXT TRANSCRIPT:\n{ocr_text}"},
                ],
            )
            raw = resp.choices[0].message.content or "{}"
            data = json.loads(raw)
            return ExtractedDocument.model_validate(data), 0.9, "ok"
        except Exception as exc:  # noqa: BLE001 — degrade to offline extractor
            _handle_openai_error(exc)

    from app.core import extraction

    res = extraction.extract_from_text(ocr_text)
    # 'fallback' only when GPT-4o was actually attempted and failed. When OpenAI is
    # switched off, the rule extractor IS the intended engine — not a degradation.
    status = "fallback" if (settings.use_openai and settings.openai_configured) else "ok"
    return res.document, res.confidence, status


# --------------------------------------------------------------------------- #
# Stage 3: Embeddings — 1536-dim vectors for semantic scheme matching
# --------------------------------------------------------------------------- #
def embed_text(text: str) -> list[float]:
    # Offline by default — deterministic hashed vectors, no network. Real
    # embeddings only when OpenAI is explicitly enabled.
    if settings.demo_mode or not settings.use_openai:
        return _pseudo_embedding(text)
    try:
        resp = _client().embeddings.create(
            model=settings.openai_embedding_model, input=text
        )
        return resp.data[0].embedding
    except Exception as exc:
        _handle_openai_error(exc)
        # Never propagate — scheme matching must keep working offline.
        return _pseudo_embedding(text)


def _pseudo_embedding(text: str) -> list[float]:
    """Deterministic hashed embedding. Not semantically meaningful, but stable and
    L2-normalized so cosine math behaves. Live mode uses real embeddings; the
    demo recommender leans on rule-based scoring for meaningful matches."""
    vec = [0.0] * EMBEDDING_DIM
    tokens = [t for t in text.lower().split() if t]
    for tok in tokens:
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        # spread each token across a few dimensions
        for i in range(8):
            idx = struct.unpack_from(">I", digest, i * 4 % 28)[0] % EMBEDDING_DIM
            sign = 1.0 if digest[i] & 1 else -1.0
            vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return max(0.0, min(1.0, dot / (na * nb)))
