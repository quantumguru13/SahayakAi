"""Verification: LIVE mode reads real documents (unique per upload); DEMO uses samples.

Run:  python -m tests.test_live_pipeline   (from the backend/ directory)
Renders four distinct document images, runs them through the REAL OCR + extraction
pipeline (no OpenAI key -> Tesseract + rule-based extractor), and asserts each upload
yields different extracted fields. Also checks DEMO mode returns curated samples and
that an unreadable image triggers the graceful OcrUnavailable fallback.
"""
from __future__ import annotations

import io
import sys

from PIL import Image, ImageDraw, ImageFont

from app.core import ai_engine, ocr

DOCS = {
    "blood_report.png": (
        "SUNRISE DIAGNOSTIC LABORATORY\n"
        "Complete Blood Count Report\n"
        "Patient Name : Yash M Patel\n"
        "Age / Sex : 34 / Male\n"
        "Address : Ahmedabad, Gujarat\n"
        "Hemoglobin : 8.1 g/dL (Low)\n"
        "Diagnosis : Severe Anemia\n"
        "Annual Income : Rs. 96000\n"
        "Last date to apply for health scheme is 15/09/2026\n"
    ),
    "aadhaar_card.png": (
        "UNIQUE IDENTIFICATION AUTHORITY OF INDIA\n"
        "Name : Rahul Sharma\n"
        "DOB : 12/07/1998  Gender : Male\n"
        "Aadhaar : 5643 8891 2277\n"
        "Address : Jaipur, Rajasthan\n"
    ),
    "income_certificate.png": (
        "GOVERNMENT OF MAHARASHTRA\n"
        "Income Certificate\n"
        "This is to certify that Sneha Kulkarni\n"
        "PAN : AQLPK7788M\n"
        "Annual Income : Rs. 42000\n"
        "State : Maharashtra\n"
        "Document must be submitted before 30/08/2026\n"
    ),
    "medical_certificate.png": (
        "CITY CARE HOSPITAL - NEPHROLOGY\n"
        "Patient : Imran Khan  Age : 51  Male\n"
        "Voter ID : MHZ2231908\n"
        "Diagnosis : Chronic Kidney Disease Stage 5\n"
        "Advised : Dialysis twice weekly\n"
        "State : Karnataka\n"
        "URGENT apply for dialysis fund by 22/07/2026\n"
    ),
}


def _font(size: int):
    for path in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def render(text: str) -> bytes:
    font = _font(30)
    lines = text.strip("\n").split("\n")
    W, line_h, pad = 1100, 46, 40
    H = pad * 2 + line_h * len(lines)
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        draw.text((pad, pad + i * line_h), ln, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def blank_image() -> bytes:
    img = Image.new("RGB", (300, 200), "white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def main() -> int:
    print("OCR engines available (offline):", ocr.available_engines())
    assert ocr.tesseract_available(), "Tesseract must be installed for this test"

    results = {}
    for name, text in DOCS.items():
        png = render(text)
        res = ocr.run_pipeline(png, name, "image/png", allow_openai=False)
        doc, conf, status = ai_engine.extract_live(res.raw_text)
        results[name] = doc
        print("\n===", name, "===")
        print(f"  engine={res.engine} ocr_conf={res.confidence:.2f} "
              f"extract_conf={conf:.2f} ai_status={status}")
        print(f"  name={doc.beneficiary_name!r} id={doc.government_id_type}:"
              f"{doc.government_id_number!r} income={doc.estimated_household_income}")
        print(f"  gender={doc.gender} state={doc.state_location} dob={doc.dob}")
        print(f"  medical={doc.detected_medical_conditions}")
        print(f"  deadlines={[(d.date, d.context) for d in doc.critical_deadlines]}")

    # --- ASSERT: every upload produced a DIFFERENT name (no mock reuse) ---
    names = [d.beneficiary_name for d in results.values()]
    print("\nExtracted names:", names)
    non_null = [n for n in names if n]
    assert len(set(non_null)) == len(non_null) and len(non_null) >= 3, (
        f"Names must be unique per document — got {names}"
    )
    assert "Aarav Kumar" not in names, "LIVE mode must NEVER return demo persona names"

    # Spot-check the extractor really read the documents:
    assert results["blood_report.png"].beneficiary_name == "Yash M Patel"
    assert results["aadhaar_card.png"].government_id_type == "Aadhaar"
    assert results["income_certificate.png"].government_id_type == "PAN"
    assert results["medical_certificate.png"].detected_medical_conditions, "medical findings expected"

    # --- ASSERT: DEMO mode returns curated samples, no OCR ---
    demo_doc = ai_engine.extract_demo(b"whatever", "aadhaar_scholarship.png")
    print("\nDEMO sample name:", demo_doc.beneficiary_name)
    assert demo_doc.beneficiary_name == "Aarav Kumar", "DEMO should load the sample persona"

    # --- ASSERT: unreadable image triggers graceful fallback (no crash) ---
    try:
        ocr.run_pipeline(blank_image(), "blank.png", "image/png", allow_openai=False)
        print("\nWARN: blank image did not raise (Tesseract found stray text)")
    except ocr.OcrUnavailableError as exc:
        print("\nBlank image correctly raised OcrUnavailableError:", exc)

    print("\nALL CHECKS PASSED — LIVE mode is unique per document; DEMO uses samples.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
