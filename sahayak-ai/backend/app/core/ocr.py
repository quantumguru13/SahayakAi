"""Real OCR pipeline — image preprocessing + multi-engine text extraction.

This module powers **LIVE mode**. It never returns canned/sample data: every call
transcribes the actual bytes the user uploaded. The pipeline is:

    bytes (image / PDF)
        -> preprocessing (deskew, denoise, sharpen, adaptive threshold, resize)
        -> OCR engine   (GPT-4o Vision if a key exists, else EasyOCR, else Tesseract)
        -> raw text + confidence
        -> (if confidence is low) secondary engine, keep the better result

Every heavy dependency (OpenCV, EasyOCR/torch, PyMuPDF, pytesseract) is imported
lazily so the FastAPI app always boots — even on a machine where only some engines
are installed. If *no* engine can produce text, we raise ``OcrUnavailableError`` so
the API can offer the "Retry / Switch to Demo" fallback instead of crashing.
"""
from __future__ import annotations

import base64
import io
import logging
from dataclasses import dataclass, field

logger = logging.getLogger("sahayak.ocr")

# Below this mean-confidence (0-1) we run a second engine and keep the better read.
LOW_CONFIDENCE_THRESHOLD = 0.55
# Minimum characters for a read to count as "usable" text.
MIN_USABLE_CHARS = 8

# Shown verbatim in the UI when LIVE mode has no engine to read with. LIVE never
# substitutes sample data, so this message has to be actionable on its own.
NO_ENGINE_MESSAGE = (
    "No offline OCR engine is installed, so Live mode cannot read this document.\n\n"
    "Install Tesseract OCR (recommended — fast, fully offline):\n"
    "  Windows:  winget install --id UB-Mannheim.TesseractOCR\n"
    "            or download from https://github.com/UB-Mannheim/tesseract/wiki\n"
    "  macOS:    brew install tesseract\n"
    "  Linux:    sudo apt-get install tesseract-ocr\n\n"
    "If tesseract.exe is installed but not on your PATH, set TESSERACT_CMD in "
    "backend/.env to its full path, e.g.\n"
    "  TESSERACT_CMD=C:\\Program Files\\Tesseract-OCR\\tesseract.exe\n\n"
    "Then restart the backend. Demo mode remains available in the meantime."
)


class OcrUnavailableError(RuntimeError):
    """Raised when no OCR engine could transcribe the document.

    Carries the list of engines that were attempted so the caller can surface a
    helpful message and the automatic Demo-mode fallback.

    ``no_engines`` distinguishes the two failure shapes:
      * True  — the machine has NO usable OCR engine at all (nothing installed,
                or the only engine was GPT-4o and its key is dead). The caller
                should fall back to DEMO mode so the app still works.
      * False — engines exist but none could read *this* document. The caller
                should offer "Retry OCR / Switch to Demo" instead.
    """

    def __init__(
        self,
        message: str,
        attempted: list[str] | None = None,
        no_engines: bool = False,
    ) -> None:
        super().__init__(message)
        self.attempted = attempted or []
        self.no_engines = no_engines


@dataclass
class OcrResult:
    """Everything the pipeline produced — including debug-panel imagery."""

    raw_text: str
    confidence: float                 # 0-1 mean OCR confidence
    engine: str                       # "gpt-4o-vision" | "easyocr" | "tesseract" | "pdf-text"
    original_image_b64: str | None = None      # data URI (PNG/JPEG) of the upload
    preprocessed_image_b64: str | None = None  # data URI of the cleaned image fed to OCR
    engines_attempted: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# Capability probing (lazy, cached) — lets the UI report which engines exist.
# --------------------------------------------------------------------------- #
def _has(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


# winget/the UB-Mannheim installer frequently leave tesseract.exe off PATH, so we
# look in the standard install locations before declaring it missing.
_WINDOWS_TESSERACT_PATHS = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe",
    r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe",
    r"%PROGRAMFILES%\Tesseract-OCR\tesseract.exe",
)


def resolve_tesseract_cmd() -> str | None:
    """Locate tesseract.exe — explicit TESSERACT_CMD, then PATH, then the usual
    Windows install directories. Returns the path it configured, or None."""
    import os
    import shutil

    candidates: list[str] = []
    try:
        from app.core.config import settings

        if settings.tesseract_cmd.strip():
            candidates.append(settings.tesseract_cmd.strip())
    except Exception:  # noqa: BLE001 — config unavailable (e.g. direct unit use)
        pass

    on_path = shutil.which("tesseract")
    if on_path:
        candidates.append(on_path)
    candidates.extend(os.path.expandvars(p) for p in _WINDOWS_TESSERACT_PATHS)

    for cand in candidates:
        if cand and os.path.isfile(cand):
            return cand
    return None


def tesseract_available() -> bool:
    if not _has("pytesseract"):
        return False
    try:
        import pytesseract

        cmd = resolve_tesseract_cmd()
        if cmd:
            pytesseract.pytesseract.tesseract_cmd = cmd
        pytesseract.get_tesseract_version()
        return True
    except Exception:  # noqa: BLE001 — binary not installed / not on PATH
        return False


def easyocr_available() -> bool:
    return _has("easyocr") and _has("torch")


def opencv_available() -> bool:
    return _has("cv2") and _has("numpy")


def available_engines(include_openai: bool = False) -> list[str]:
    """Usable engines in preference order — offline engines first.

    EasyOCR leads when installed: it is markedly more accurate on Indian identity
    documents (Aadhaar's mixed Devanagari/Latin layout). Tesseract is the always-
    available fallback and needs no model download. GPT-4o Vision is last and
    opt-in only (see settings.use_openai), so LIVE stays fully offline.
    """
    engines: list[str] = []
    if easyocr_available():
        engines.append("easyocr")
    if tesseract_available():
        engines.append("tesseract")
    if include_openai:
        engines.append("gpt-4o-vision")
    return engines


# --------------------------------------------------------------------------- #
# Image preprocessing (OpenCV) — deskew, denoise, sharpen, threshold, resize.
# --------------------------------------------------------------------------- #
def _to_data_uri(png_bytes: bytes, mime: str = "image/png") -> str:
    return f"data:{mime};base64,{base64.b64encode(png_bytes).decode('ascii')}"


def preprocess_image(content: bytes) -> tuple[bytes, bytes, list[str]]:
    """Return ``(original_png, preprocessed_png, notes)``.

    Gracefully degrades: if OpenCV isn't installed we return the original bytes
    for both slots so the pipeline still runs (Tesseract/EasyOCR can handle raw
    images) and the debug panel simply shows the unprocessed image.
    """
    notes: list[str] = []
    if not opencv_available():
        notes.append("OpenCV not installed — preprocessing skipped")
        return content, content, notes

    import cv2
    import numpy as np

    arr = np.frombuffer(content, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        notes.append("Could not decode image — preprocessing skipped")
        return content, content, notes

    original_png = cv2.imencode(".png", img)[1].tobytes()

    # 1) Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2) Resize — upscale small images so glyphs are large enough for OCR.
    h, w = gray.shape[:2]
    longest = max(h, w)
    if longest < 1600:
        scale = 1600.0 / longest
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
        notes.append(f"upscaled x{scale:.2f}")

    # 3) Denoise
    gray = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)

    # 4) Deskew — estimate text angle from foreground pixels.
    try:
        thr = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
        coords = np.column_stack(np.where(thr > 0))
        if coords.size:
            angle = cv2.minAreaRect(coords)[-1]
            angle = -(90 + angle) if angle < -45 else -angle
            if abs(angle) > 0.5:
                (gh, gw) = gray.shape[:2]
                m = cv2.getRotationMatrix2D((gw / 2, gh / 2), angle, 1.0)
                gray = cv2.warpAffine(
                    gray, m, (gw, gh),
                    flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE,
                )
                notes.append(f"deskewed {angle:.1f}°")
    except Exception as exc:  # noqa: BLE001
        notes.append(f"deskew skipped ({exc})")

    # 5) Sharpen — unsharp mask.
    blur = cv2.GaussianBlur(gray, (0, 0), 3)
    gray = cv2.addWeighted(gray, 1.5, blur, -0.5, 0)

    # 6) Adaptive threshold — binarize for crisp glyph edges.
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )

    preprocessed_png = cv2.imencode(".png", binary)[1].tobytes()
    return original_png, preprocessed_png, notes


# --------------------------------------------------------------------------- #
# PDF handling — embedded text first, then rasterize page 1 for OCR.
# --------------------------------------------------------------------------- #
def _pdf_embedded_text(content: bytes) -> str:
    try:
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content))
        return "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    except Exception:  # noqa: BLE001
        return ""


def _pdf_first_page_png(content: bytes) -> bytes | None:
    """Render the first PDF page to PNG bytes (PyMuPDF — no system deps)."""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(stream=content, filetype="pdf")
        if doc.page_count == 0:
            return None
        page = doc.load_page(0)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for sharper OCR
        return pix.tobytes("png")
    except Exception as exc:  # noqa: BLE001
        logger.warning("PDF rasterization failed: %s", exc)
        return None


# --------------------------------------------------------------------------- #
# Individual OCR engines — each returns (text, confidence 0-1).
# --------------------------------------------------------------------------- #
def _ocr_tesseract(image_bytes: bytes) -> tuple[str, float]:
    import pytesseract
    from PIL import Image

    img = Image.open(io.BytesIO(image_bytes))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    words, confs = [], []
    for txt, conf in zip(data.get("text", []), data.get("conf", [])):
        if txt and txt.strip():
            words.append(txt)
            try:
                c = float(conf)
            except (TypeError, ValueError):
                c = -1.0
            if c >= 0:
                confs.append(c)
    text = pytesseract.image_to_string(img).strip()
    if not text:
        text = " ".join(words).strip()
    confidence = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return text, round(confidence, 4)


# Cached EasyOCR reader — model load is expensive; do it once.
_easyocr_reader = None


def _get_easyocr_reader():
    global _easyocr_reader
    if _easyocr_reader is None:
        import easyocr

        _easyocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    return _easyocr_reader


def _ocr_easyocr(image_bytes: bytes) -> tuple[str, float]:
    import numpy as np
    from PIL import Image

    img = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
    reader = _get_easyocr_reader()
    results = reader.readtext(img, detail=1, paragraph=False)
    lines, confs = [], []
    for _box, txt, conf in results:
        if txt and txt.strip():
            lines.append(txt)
            confs.append(float(conf))
    text = "\n".join(lines).strip()
    confidence = (sum(confs) / len(confs)) if confs else 0.0
    return text, round(confidence, 4)


def _ocr_gpt4o(content: bytes, mime: str, chat_model: str, api_key: str) -> tuple[str, float]:
    from openai import OpenAI

    b64 = base64.b64encode(content).decode("ascii")
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=chat_model,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "You are an OCR engine. Transcribe ALL text you can read "
                "from the document image verbatim, preserving line breaks. Output only "
                "the raw transcribed text.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Transcribe this document:"},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
        ],
    )
    text = (resp.choices[0].message.content or "").strip()
    # Vision transcription is high fidelity; assign a strong nominal confidence.
    return text, 0.95 if text else 0.0


# --------------------------------------------------------------------------- #
# Orchestrator — preprocess, pick engines, run with low-confidence retry.
# --------------------------------------------------------------------------- #
def run_pipeline(
    content: bytes,
    filename: str,
    content_type: str | None,
    *,
    allow_openai: bool = False,
    openai_api_key: str = "",
    openai_chat_model: str = "gpt-4o",
    on_openai_error=None,
) -> OcrResult:
    """Transcribe the uploaded document. Raises ``OcrUnavailableError`` on total
    failure so the API can offer the Demo-mode fallback (never a crash, never a
    fabricated transcript)."""
    is_pdf = (content_type or "").endswith("pdf") or filename.lower().endswith(".pdf")
    attempted: list[str] = []
    notes: list[str] = []

    # ---- PDFs: prefer the embedded text layer (fast + perfectly accurate) ----
    ocr_source = content
    original_png = content
    if is_pdf:
        embedded = _pdf_embedded_text(content)
        page_png = _pdf_first_page_png(content)
        if page_png:
            original_png = page_png
        if len(embedded) >= MIN_USABLE_CHARS:
            preview = page_png or content
            return OcrResult(
                raw_text=embedded,
                confidence=0.99,
                engine="pdf-text",
                original_image_b64=_to_data_uri(preview) if page_png else None,
                preprocessed_image_b64=_to_data_uri(preview) if page_png else None,
                engines_attempted=["pdf-text"],
                notes=["extracted embedded PDF text layer"],
            )
        # Scanned PDF (no text layer) — OCR the rendered page.
        if page_png is None:
            raise OcrUnavailableError(
                "PDF has no text layer and could not be rasterized for OCR.",
                attempted=["pdf-text"],
            )
        ocr_source = page_png
        notes.append("scanned PDF — rasterized page 1 for OCR")

    # ---- Preprocess the image we will feed to the OCR engines ----
    original_png, preprocessed_png, pp_notes = preprocess_image(ocr_source)
    notes.extend(pp_notes)

    # ---- Engine order: EasyOCR -> Tesseract -> GPT-4o Vision (opt-in) ----
    engine_chain: list[str] = []
    if easyocr_available():
        engine_chain.append("easyocr")
    if tesseract_available():
        engine_chain.append("tesseract")
    if allow_openai and openai_api_key.strip():
        engine_chain.append("gpt-4o-vision")

    if not engine_chain:
        raise OcrUnavailableError(NO_ENGINE_MESSAGE, attempted=[], no_engines=True)

    # Local engines are the safety net when GPT-4o Vision is unreachable (dead key,
    # offline). If the chain is GPT-4o only, an OpenAI failure means no engines left.
    local_engines = [e for e in engine_chain if e != "gpt-4o-vision"]

    best_text, best_conf, best_engine = "", 0.0, ""
    for engine in engine_chain:
        attempted.append(engine)
        try:
            if engine == "gpt-4o-vision":
                mime = content_type or ("application/pdf" if is_pdf else "image/png")
                # GPT-4o reads the original (it does its own cleanup) — send the
                # rendered/original image, not the binarized one.
                src = ocr_source if is_pdf else content
                text, conf = _ocr_gpt4o(src, mime, openai_chat_model, openai_api_key)
            elif engine == "easyocr":
                text, conf = _ocr_easyocr(preprocessed_png)
            else:  # tesseract
                text, conf = _ocr_tesseract(preprocessed_png)
        except Exception as exc:  # noqa: BLE001 — try the next engine
            logger.warning("OCR engine %s failed: %s", engine, exc)
            notes.append(f"{engine} error: {exc}")
            # Let the caller record an OpenAI auth/connection failure so the whole
            # app stops advertising GPT-4o and degrades to the local engines.
            if engine == "gpt-4o-vision" and on_openai_error is not None:
                try:
                    on_openai_error(exc)
                except Exception:  # noqa: BLE001 — never let bookkeeping break OCR
                    pass
                if local_engines:
                    notes.append(
                        "GPT-4o Vision unavailable — falling back to "
                        + " → ".join(local_engines)
                    )
            continue

        if len(text) >= MIN_USABLE_CHARS and conf > best_conf:
            best_text, best_conf, best_engine = text, conf, engine

        # Good enough? Stop. Otherwise fall through to the next (secondary) engine.
        if best_conf >= LOW_CONFIDENCE_THRESHOLD and len(best_text) >= MIN_USABLE_CHARS:
            break
        if best_text:
            notes.append(f"{engine} confidence {best_conf:.2f} < {LOW_CONFIDENCE_THRESHOLD} — trying secondary engine")

    if len(best_text) < MIN_USABLE_CHARS:
        # Every attempt failed. If the only engine was GPT-4o Vision (now known to
        # be unreachable) there is no local OCR left — flag it so the caller can
        # switch to DEMO rather than showing a dead-end "Retry" button.
        raise OcrUnavailableError(
            "OCR ran but could not read usable text from the document.",
            attempted=attempted,
            no_engines=not local_engines,
        )

    return OcrResult(
        raw_text=best_text,
        confidence=best_conf,
        engine=best_engine,
        original_image_b64=_to_data_uri(original_png),
        preprocessed_image_b64=_to_data_uri(preprocessed_png),
        engines_attempted=attempted,
        notes=notes,
    )
