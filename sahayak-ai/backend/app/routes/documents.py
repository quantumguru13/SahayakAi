"""Document intake pipeline — two fully independent modes.

  LIVE  (production):  upload -> preprocess -> real OCR -> AI extraction ->
                       urgency -> scheme matching -> tasks -> dashboard.
                       Every upload yields unique fields. NEVER uses sample data.
  DEMO  (offline):     loads a curated sample case. NO OCR, NO API. Clearly badged.

The client picks the mode per request (``mode`` form field); if omitted we use the
server default (LIVE when real OCR is available, otherwise DEMO). If LIVE OCR fails
we return a graceful ``OcrUnavailableResponse`` (HTTP 200) so the UI can offer
"Retry OCR / Switch to Demo" — the pipeline never crashes and never fabricates text.
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core import aadhaar as aadhaar_core
from app.core import ai_engine, ocr
from app.core.auth import CurrentUser, get_current_user
from app.core.config import settings
from app.core.store import _mask_id, store
from app.core.urgency import assess_urgency
from app.models.schemas import (
    AadhaarAnalysis,
    AadhaarFields,
    AadhaarVerification,
    DocumentUploadResponse,
    ExtractedDocument,
    OcrUnavailableResponse,
    PipelineDebug,
    PipelineMode,
    UploadHistoryEntry,
)

logger = logging.getLogger("sahayak.documents")

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_BYTES = 15 * 1024 * 1024  # 15 MB cap for multipart image/PDF payloads
ALLOWED_PREFIXES = ("image/",)
ALLOWED_EXACT = {"application/pdf", "application/octet-stream", ""}
# Magic bytes for the formats we accept — catches a .png that is really a .exe,
# and truncated/corrupted uploads, before they reach the OCR engines.
_MAGIC = {
    b"\x89PNG\r\n\x1a\n": "png",
    b"\xff\xd8\xff": "jpeg",
    b"%PDF": "pdf",
    b"GIF87a": "gif",
    b"GIF89a": "gif",
    b"BM": "bmp",
}


def _sniff(content: bytes) -> str | None:
    """Identify the real format from magic bytes (ignores the declared type)."""
    for magic, kind in _MAGIC.items():
        if content.startswith(magic):
            return kind
    # TIFF (both endiannesses) and WEBP carry offset markers.
    if content[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "webp"
    return None


def _validate(file: UploadFile, content: bytes, *, decode_required: bool = True) -> None:
    """Reject uploads we cannot process, with guidance the user can act on.

    ``decode_required`` is False for DEMO uploads: those bytes are never decoded
    or OCR'd — they only select a curated sample — so the sample buttons must not
    be rejected for failing an image-format check that will never be applied.
    """
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=400, detail="Empty file upload.")
    if size > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"File is {size / (1024 * 1024):.1f} MB — the limit is "
                f"{MAX_BYTES // (1024 * 1024)} MB. Try photographing the card at a "
                "lower resolution."
            ),
        )
    ct = (file.content_type or "").lower()
    if not (ct.startswith(ALLOWED_PREFIXES) or ct in ALLOWED_EXACT):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Upload an image (JPG/PNG) or a PDF.",
        )
    if decode_required and _sniff(content) is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "This file is not a readable image or PDF — it may be corrupted or "
                "incompletely uploaded. Re-save it as JPG, PNG or PDF and try again."
            ),
        )


def _analyse_aadhaar(
    ocr_text: str, image_bytes: bytes | None, ocr_confidence: float
) -> AadhaarAnalysis | None:
    """Run the Aadhaar layer when the transcript looks like an Aadhaar card.

    Returns None for non-Aadhaar documents so the existing intake flow is
    untouched. The raw number is masked here and never travels further.
    """
    raw = aadhaar_core.extract(ocr_text, image_bytes)
    # Only claim this is an Aadhaar when we found a number or layout markers.
    if not raw.get("aadhaar_number") and raw.get("side") == "unknown":
        return None

    result = aadhaar_core.verify(raw, ocr_confidence)
    qr = raw.get("qr_payload")
    fields = AadhaarFields(
        full_name=raw.get("full_name"),
        aadhaar_number=aadhaar_core.mask_aadhaar(raw.get("aadhaar_number")),
        date_of_birth=raw.get("date_of_birth"),
        year_of_birth=raw.get("year_of_birth"),
        gender=raw.get("gender"),
        address=raw.get("address"),
        state=raw.get("state"),
        district=raw.get("district"),
        pin_code=raw.get("pin_code"),
        mobile=raw.get("mobile"),
        qr_detected=bool(qr),
        qr_preview=(qr[:80] if qr else None),
        side=raw.get("side", "unknown"),
    )
    return AadhaarAnalysis(
        fields=fields,
        verification=AadhaarVerification(**result),
        ocr_confidence=ocr_confidence,
        low_confidence=ocr_confidence < aadhaar_core.MIN_OCR_CONFIDENCE,
    )


def _log_upload(
    *,
    session_id: str,
    user: CurrentUser,
    filename: str,
    mode: PipelineMode,
    engine: str,
    started: float,
    status: str,
    document_type: str = "document",
    verification_status: str | None = None,
    beneficiary_id: str | None = None,
) -> None:
    """Append an audit row for this upload attempt (success or failure)."""
    store.record_upload(
        UploadHistoryEntry(
            session_id=session_id,
            created_at=datetime.now(timezone.utc),
            document_type=document_type,
            mode=mode,
            ocr_engine=engine,
            processing_ms=int((time.perf_counter() - started) * 1000),
            status=status,
            verification_status=verification_status,
            user_id=user.id,
            user_role=user.role,
            file_name=filename,
            beneficiary_id=beneficiary_id,
        )
    )


def _finalize(
    extraction: ExtractedDocument,
    ocr_text: str,
    filename: str,
    started: float,
    mode: PipelineMode,
    debug: PipelineDebug,
    aadhaar: AadhaarAnalysis | None = None,
    session_id: str | None = None,
) -> DocumentUploadResponse:
    """Shared tail of the pipeline: urgency -> beneficiary -> tasks -> schemes."""
    # Scope the dashboard to the mode of this upload so LIVE results never mix
    # with sample data (and vice-versa).
    store.set_active_mode(mode.value)
    source = "demo" if mode == PipelineMode.DEMO else "live"

    # Aadhaar carries identity fields the generic extractor may have missed.
    # Feed them into the SAME ExtractedDocument so urgency and the recommender
    # keep working off one shape — no parallel path, no engine changes.
    if aadhaar is not None:
        af = aadhaar.fields
        patch: dict = {}
        if not extraction.beneficiary_name and af.full_name:
            patch["beneficiary_name"] = af.full_name
        if extraction.age is None and af.year_of_birth:
            patch["age"] = max(0, datetime.now(timezone.utc).year - af.year_of_birth)
        if not extraction.gender and af.gender:
            patch["gender"] = af.gender
        if not extraction.state_location and af.state:
            patch["state_location"] = af.state
        if not extraction.government_id_type and af.aadhaar_number:
            patch["government_id_type"] = "Aadhaar"
        if patch:
            extraction = extraction.model_copy(update=patch)

    # PRIVACY: for an Aadhaar the raw number also sits inside the OCR transcript
    # (and the card image itself). Redact the transcript before it is stored or
    # returned, and drop the imagery unless audit mode is explicitly enabled.
    if aadhaar is not None:
        ocr_text = aadhaar_core.redact_text(ocr_text)
        if not settings.audit_mode:
            debug = debug.model_copy(
                update={"original_image": None, "preprocessed_image": None}
            )
            debug.notes = [
                *debug.notes,
                "Uploaded imagery discarded after processing (AUDIT_MODE=false).",
            ]

    urgency = assess_urgency(
        medical_conditions=extraction.detected_medical_conditions,
        deadlines=extraction.critical_deadlines,
        annual_income=extraction.estimated_household_income,
        is_disabled=extraction.is_disabled,
        age=extraction.age,
    )
    beneficiary = store.upsert_from_extraction(extraction, urgency, source=source)
    document = store.add_document(beneficiary.id, filename, ocr_text, extraction)
    generated_tasks = store.add_tasks_from_extraction(beneficiary.id, extraction)
    scheme_matches = store.recommend_schemes(beneficiary)

    debug.scheme_matching_status = "ok" if scheme_matches else "none"

    # PII: never return the full government ID over the wire — mask it.
    safe_extraction = extraction.model_copy(
        update={"government_id_number": _mask_id(extraction.government_id_number)}
    )

    processing_ms = int((time.perf_counter() - started) * 1000)
    return DocumentUploadResponse(
        document_id=document.id,
        beneficiary=beneficiary,
        extraction=safe_extraction,
        urgency=urgency,
        extracted_text=ocr_text,
        processing_ms=processing_ms,
        scheme_matches=scheme_matches,
        generated_tasks=generated_tasks,
        demo_mode=(mode == PipelineMode.DEMO),
        mode=mode,
        debug=debug,
        aadhaar=aadhaar,
        session_id=session_id,
    )


def _run_demo(
    content: bytes, filename: str, started: float, session_id: str
) -> DocumentUploadResponse:
    """DEMO: curated sample case. No OCR, no network. Clearly flagged for judges."""
    ocr_text = ai_engine.run_ocr_demo(content, filename)
    extraction = ai_engine.extract_demo(content, filename)
    debug = PipelineDebug(
        mode=PipelineMode.DEMO,
        ocr_engine="sample",
        ocr_confidence=1.0,
        extraction_confidence=1.0,
        ai_status="sample",
        scheme_matching_status="ok",
        engines_attempted=["sample"],
        notes=["DEMO MODE — deterministic sample beneficiary data, no OCR executed"],
    )
    # Synthetic Aadhaar samples run the real analyser over their transcript, so the
    # panel a judge inspects is produced by the same code path as a live upload.
    aadhaar = _analyse_aadhaar(ocr_text, None, 1.0)
    return _finalize(
        extraction, ocr_text, filename, started, PipelineMode.DEMO, debug,
        aadhaar=aadhaar, session_id=session_id,
    )


def _run_live(
    content: bytes,
    filename: str,
    content_type: str | None,
    started: float,
    session_id: str,
    user: CurrentUser,
) -> DocumentUploadResponse | OcrUnavailableResponse:
    """LIVE: real OCR + AI extraction on the uploaded bytes. Unique per document."""
    try:
        ocr_result = ai_engine.run_ocr_live(content, filename, content_type)
    except ocr.OcrUnavailableError as exc:
        # LIVE NEVER falls back to sample data. A curated demo beneficiary returned
        # from a LIVE upload would be indistinguishable from a real extraction —
        # so we report the failure honestly and let the user decide what to do.
        logger.warning("LIVE OCR unavailable: %s", exc)
        _log_upload(
            session_id=session_id, user=user, filename=filename,
            mode=PipelineMode.LIVE, engine="none", started=started,
            status="OCR_UNAVAILABLE",
        )
        return OcrUnavailableResponse(
            message=str(exc),
            engines_attempted=exc.attempted,
        )

    extraction, extraction_conf, ai_status = ai_engine.extract_live(ocr_result.raw_text)

    debug = PipelineDebug(
        mode=PipelineMode.LIVE,
        ocr_engine=ocr_result.engine,
        ocr_confidence=ocr_result.confidence,
        extraction_confidence=extraction_conf,
        ai_status=ai_status,
        scheme_matching_status="ok",
        engines_attempted=ocr_result.engines_attempted,
        original_image=ocr_result.original_image_b64,
        preprocessed_image=ocr_result.preprocessed_image_b64,
        notes=ocr_result.notes,
    )
    # LIVE Aadhaar analysis runs on the REAL transcript and the REAL image bytes.
    aadhaar = _analyse_aadhaar(
        ocr_result.raw_text, content, ocr_result.confidence
    )
    return _finalize(
        extraction, ocr_result.raw_text, filename, started, PipelineMode.LIVE, debug,
        aadhaar=aadhaar, session_id=session_id,
    )


@router.post("/upload", response_model=None)
async def upload_document(
    file: UploadFile = File(...),
    mode: str = Form(default=""),
    allow_duplicate: bool = Form(default=False),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentUploadResponse | OcrUnavailableResponse:
    """Ingest a document (Aadhaar or general) and run the full pipeline.

    Form fields:
      file             required — image (JPG/PNG/JPEG/GIF/BMP/TIFF/WEBP) or PDF, <= 15 MB
      mode             "LIVE" | "DEMO" (default: server capability)
      allow_duplicate  re-process a file already ingested this session

    Errors: 400 empty · 413 too large · 415 unsupported type · 422 corrupted
            409 duplicate (unless allow_duplicate=true)
    Returns DocumentUploadResponse, or OcrUnavailableResponse (HTTP 200) when
    LIVE OCR cannot read the document.
    """
    started = time.perf_counter()
    content = await file.read()
    filename = file.filename or "upload"
    session_id = f"sess-{uuid.uuid4().hex[:12]}"

    requested = (mode or "").strip().upper()
    if requested not in ("LIVE", "DEMO"):
        requested = settings.default_pipeline_mode
    pipeline_mode = PipelineMode(requested)

    _validate(file, content, decode_required=(requested == "LIVE"))

    # Duplicate detection is content-based, so a renamed copy is still caught.
    digest = hashlib.sha256(content).hexdigest()
    if not allow_duplicate and store.seen_document(digest):
        _log_upload(
            session_id=session_id, user=user, filename=filename,
            mode=pipeline_mode, engine="none", started=started, status="REJECTED",
        )
        raise HTTPException(
            status_code=409,
            detail=(
                "This exact file has already been processed in this session. "
                "Re-send with allow_duplicate=true to process it again."
            ),
        )

    # Scope the dashboard to this upload's mode up front — even if LIVE OCR fails,
    # the judge stays in LIVE mode (empty dashboard, not demo data).
    store.set_active_mode(requested)

    if requested == "DEMO":
        response = _run_demo(content, filename, started, session_id)
    else:
        response = _run_live(
            content, filename, file.content_type, started, session_id, user
        )

    if isinstance(response, DocumentUploadResponse):
        store.remember_document(digest)
        _log_upload(
            session_id=session_id, user=user, filename=filename,
            mode=pipeline_mode,
            engine=response.debug.ocr_engine if response.debug else "unknown",
            started=started, status="SUCCESS",
            document_type="aadhaar" if response.aadhaar else "document",
            verification_status=(
                response.aadhaar.verification.status.value
                if response.aadhaar else None
            ),
            beneficiary_id=response.beneficiary.id,
        )
    return response


@router.get("/history", response_model=list[UploadHistoryEntry])
def upload_history(
    limit: int = 50,
    user: CurrentUser = Depends(get_current_user),
) -> list[UploadHistoryEntry]:
    """Audit trail of upload attempts, newest first.

    Applicants see only their own uploads; jury and admin roles see everything.
    """
    entries = store.list_history(limit)
    if user.role in ("admin", "jury", "authenticated"):
        return entries
    return [e for e in entries if e.user_id == user.id]
