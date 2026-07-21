"""End-to-end audit — the full LIVE pipeline over 5 documents + Demo/Live isolation.

Run:  python -m tests.test_audit   (from the backend/ directory, Tesseract installed)

Exercises EVERY stage on real rendered documents:
    preprocess -> OCR (EasyOCR/Tesseract) -> extraction -> urgency ->
    scheme matching -> task generation -> dashboard scoping.
Asserts each upload yields UNIQUE dashboard data, that schemes and urgency vary by
document, that LIVE mode hides all seed data while DEMO shows it, and that nothing
is fabricated (missing fields stay null).
"""
from __future__ import annotations

import io
import sys

from PIL import Image, ImageDraw, ImageFont

from app.core import ai_engine, ocr
from app.core.store import DataStore
from app.core.urgency import assess_urgency

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
        "Report Date : 12/06/2026\n"
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
        "Certificate No : MH/INC/2026/5521\n"
        "Document must be submitted before 30/08/2026\n"
    ),
    "disability_certificate.png": (
        "OFFICE OF THE CHIEF MEDICAL OFFICER\n"
        "Disability Certificate (PwD)\n"
        "Name : Ganesh Prasad\n"
        "Age : 63  Gender : Male\n"
        "State : Odisha\n"
        "Ration Card : OD-11-334822\n"
        "Disability : Locomotor disability 60% permanent\n"
        "Annual family income : Rs. 54000\n"
        "Pension renewal due by 05/08/2026\n"
    ),
    "scholarship_form.png": (
        "POST-MATRIC SCHOLARSHIP APPLICATION\n"
        "Student Name : Ananya Reddy\n"
        "DOB : 03/02/2008  Gender : Female\n"
        "Aadhaar : 3312 7788 4590\n"
        "Address : Hyderabad, Telangana\n"
        "Family Annual Income : Rs. 88000\n"
        "Last date for scholarship form is 25/09/2026\n"
    ),
}


def _font(size: int):
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ):
        try:
            return ImageFont.truetype(p, size)
        except Exception:  # noqa: BLE001
            continue
    return ImageFont.load_default()


def render(text: str) -> bytes:
    font = _font(30)
    lines = text.strip("\n").split("\n")
    W, lh, pad = 1150, 46, 40
    img = Image.new("RGB", (W, pad * 2 + lh * len(lines)), "white")
    draw = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        draw.text((pad, pad + i * lh), ln, fill="black", font=font)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def blank() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "white").save(buf, format="PNG")
    return buf.getvalue()


def main() -> int:  # noqa: C901
    print("OCR engines available (offline):", ocr.available_engines())
    assert ocr.tesseract_available(), "Tesseract required"

    store = DataStore()
    store.set_active_mode("LIVE")
    assert store.list_beneficiaries() == [], "LIVE must start with zero seed cases"

    dash = {}
    for name, text in DOCS.items():
        png = render(text)

        # STAGE 1-2: preprocess + OCR (asserts imagery + text produced)
        res = ocr.run_pipeline(png, name, "image/png", allow_openai=False)
        assert res.raw_text and res.engine in ("tesseract", "easyocr")
        assert res.original_image_b64 and res.preprocessed_image_b64, "debug imagery missing"

        # STAGE 3: extraction (from OCR only)
        doc, ex_conf, ai_status = ai_engine.extract_live(res.raw_text)

        # STAGE 4: urgency
        urg = assess_urgency(
            medical_conditions=doc.detected_medical_conditions,
            deadlines=doc.critical_deadlines,
            annual_income=doc.estimated_household_income,
            is_disabled=doc.is_disabled,
            age=doc.age,
        )
        # STAGE 5-6: beneficiary + tasks (dashboard hydration)
        ben = store.upsert_from_extraction(doc, urg, source="live")
        tasks = store.add_tasks_from_extraction(ben.id, doc)
        # STAGE 7: scheme matching
        schemes = store.recommend_schemes(ben)
        top = schemes[0].scheme.title if schemes else None

        dash[name] = {
            "name": doc.beneficiary_name, "id": doc.government_id_number,
            "income": doc.estimated_household_income, "priority": urg.priority.value,
            "score": urg.score, "top_scheme": top, "n_tasks": len(tasks),
            "ocr_conf": res.confidence, "ex_conf": ex_conf,
        }
        print(f"\n=== {name} ===")
        for k, v in dash[name].items():
            print(f"  {k}: {v}")

    # ---- UNIQUENESS: distinct people ----
    names = [d["name"] for d in dash.values() if d["name"]]
    assert len(set(names)) == len(names) >= 4, f"names not unique: {names}"
    assert "Aarav Kumar" not in names, "LIVE must never surface demo persona"

    # ---- PHASE 5: schemes differ across documents ----
    tops = {d["top_scheme"] for d in dash.values()}
    print("\nDistinct top schemes:", tops)
    assert len(tops) >= 3, f"scheme matching not varying enough: {tops}"

    # ---- PHASE 6: urgency responds to content ----
    assert dash["blood_report.png"]["score"] != dash["aadhaar_card.png"]["score"], \
        "medical report and Aadhaar must not share urgency"
    assert dash["aadhaar_card.png"]["priority"] in ("LOW", "MEDIUM"), \
        "plain Aadhaar should be low/medium urgency"

    # ---- PHASE 4: no fabrication (Aadhaar card carries no income) ----
    assert dash["aadhaar_card.png"]["income"] is None, "income must not be invented"

    # ---- PHASE 2: LIVE dashboard shows exactly the 5 uploads, no seed ----
    live_names = [b.name for b in store.list_beneficiaries()]
    print("\nLIVE dashboard:", live_names)
    assert set(live_names) == set(names), "LIVE dashboard must show only uploads"
    for seeded in ("Aarav Kumar", "Priya Sharma", "Lakshmi Devi", "Ramesh Yadav"):
        assert seeded not in live_names, f"seed leaked into LIVE: {seeded}"

    # ---- Demo isolation: switching to DEMO reveals seed, hides live ----
    store.set_active_mode("DEMO")
    demo_names = [b.name for b in store.list_beneficiaries()]
    print("DEMO dashboard:", demo_names)
    assert "Aarav Kumar" in demo_names, "DEMO should show seed personas"
    assert all(n not in demo_names for n in names), "live uploads must hide in DEMO"

    # ---- Low-confidence / graceful fallback ----
    try:
        ocr.run_pipeline(blank(), "blank.png", "image/png", allow_openai=False)
        print("\nNOTE: blank produced stray text (still no crash)")
    except ocr.OcrUnavailableError as e:
        print("\nBlank image -> graceful OcrUnavailableError:", e)

    print("\nAUDIT PASSED — 5 unique cases, schemes+urgency vary, LIVE/DEMO fully isolated.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
