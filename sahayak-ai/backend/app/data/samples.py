"""Curated realistic Indian NGO documents for DEMO_MODE.

Each sample pairs a raw OCR transcript (intentionally noisy, like a phone photo)
with the ground-truth structured extraction GPT-4o would return. In demo mode the
uploaded file is deterministically mapped to one of these, guaranteeing a flawless
"magic moment" on stage with zero external API calls.
"""
from __future__ import annotations

from datetime import date, timedelta


def _future(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def _aadhaar_card(
    *,
    key: str,
    hints: list[str],
    name: str,
    number: str,
    dob: str,
    gender: str,
    address: str,
    district: str,
    state: str,
    pin: str,
    field_note: str,
    age: int,
    income: float | None,
    occupation: str | None = None,
    conditions: list[str] | None = None,
    disabled: bool = False,
    bereaved: bool = False,
    deadline: dict | None = None,
) -> dict:
    """Build one synthetic Aadhaar sample in the shape the DEMO pipeline expects.

    The transcript mimics a combined front+back capture (UIDAI header, holder
    block, then the address panel and helpline footer) so ``aadhaar.detect_side``
    reports "combined" and the layout-consistency check passes.
    """
    return {
        "key": key,
        "file_hint": hints,
        "ocr_text": (
            "GOVERNMENT OF INDIA\n"
            "भारत सरकार\n"
            "UNIQUE IDENTIFICATION AUTHORITY OF INDIA\n"
            "-------------------------------------------\n"
            f"{name}\n"
            f"DOB : {dob}\n"
            f"{gender}\n"
            f"{number}\n"
            "-------------------------------------------\n"
            f"Address : {address}, {district}, {state} - {pin}\n"
            "www.uidai.gov.in            help@uidai.gov.in\n"
            "1947\n"
            "-------------------------------------------\n"
            f"NGO FIELD RECORD: {field_note}\n"
        ),
        "extraction": {
            "beneficiary_name": name,
            "government_id_type": "Aadhaar",
            "government_id_number": number,
            "critical_deadlines": [deadline] if deadline else [],
            "detected_medical_conditions": conditions or [],
            "estimated_household_income": income,
        },
        "profile": {
            "age": age,
            "gender": gender,
            "state_location": state,
            "is_disabled": disabled,
            "is_bereaved": bereaved,
            "occupation": occupation,
        },
    }


def _aadhaar_samples() -> list[dict]:
    """Seven archetypes, each producing distinct fields and distinct schemes."""
    return [
        _aadhaar_card(
            key="aadhaar_adult_male",
            hints=["adult_male", "aadhaar_male", "ramesh_k"],
            name="Devendra Rathore", number="7260 1815 9082",
            dob="14/03/1990", gender="Male",
            address="12 Shivaji Nagar", district="Pune", state="Maharashtra",
            pin="411005",
            field_note="daily-wage construction worker, annual income Rs. 84000",
            age=36, income=84000, occupation="Daily wage labourer",
        ),
        _aadhaar_card(
            key="aadhaar_adult_female",
            hints=["adult_female", "aadhaar_female", "meera"],
            name="Anjali Deshmukh", number="5016 6131 8603",
            dob="02/11/1994", gender="Female",
            address="7 Gandhi Road", district="Nashik", state="Maharashtra",
            pin="422001",
            field_note="domestic worker, annual income Rs. 72000",
            age=32, income=72000, occupation="Domestic worker",
        ),
        _aadhaar_card(
            key="aadhaar_senior",
            hints=["senior", "oldage", "elderly", "aadhaar_senior"],
            name="Bhaskar Rao Naidu", number="3390 9960 3089",
            dob="09/06/1953", gender="Male",
            address="45 Temple Street", district="Guntur", state="Andhra Pradesh",
            pin="522002",
            field_note="no earning member, annual income Rs. 42000; hypertension on record",
            age=73, income=42000, conditions=["Hypertension"],
            deadline={"date": _future(21), "context": "Old age pension renewal"},
        ),
        _aadhaar_card(
            key="aadhaar_student",
            hints=["student", "scholarship_aadhaar", "aadhaar_student"],
            name="Nikhil Barman", number="4462 8194 8213",
            dob="18/08/2008", gender="Male",
            address="22 College Para", district="Jalpaiguri", state="West Bengal",
            pin="735101",
            field_note="class 11 student, family annual income Rs. 68000",
            age=18, income=68000, occupation="Student",
            deadline={"date": _future(30), "context": "Post-matric scholarship application"},
        ),
        _aadhaar_card(
            key="aadhaar_farmer",
            hints=["farmer", "kisan", "aadhaar_farmer"],
            name="Hariram Chaudhary", number="5518 1909 3782",
            dob="27/01/1979", gender="Male",
            address="Village Rampura", district="Sikar", state="Rajasthan",
            pin="332001",
            field_note="marginal farmer, 1.2 acre rainfed, annual income Rs. 58000",
            age=47, income=58000, occupation="Farmer",
        ),
        _aadhaar_card(
            key="aadhaar_widow",
            hints=["widow", "aadhaar_widow", "vidhwa"],
            name="Kamla Devi Meena", number="8579 7543 2313",
            dob="05/05/1980", gender="Female",
            address="Ward 4 Kotra", district="Kota", state="Rajasthan",
            pin="324001",
            field_note=(
                "widow, husband deceased 2024, two dependent children, "
                "annual income Rs. 46000"
            ),
            age=46, income=46000, bereaved=True,
            deadline={"date": _future(18), "context": "Widow pension application"},
        ),
        _aadhaar_card(
            key="aadhaar_disabled",
            hints=["disabled", "divyang", "pwd", "aadhaar_disabled"],
            name="Suresh Kumar Patel", number="6875 7491 1868",
            dob="16/09/1987", gender="Male",
            address="88 Station Road", district="Rajkot", state="Gujarat",
            pin="360001",
            field_note=(
                "locomotor disability 65% certified, annual income Rs. 51000"
            ),
            age=39, income=51000, disabled=True,
            conditions=["Locomotor disability (65%)"],
            deadline={"date": _future(12), "context": "Disability pension renewal"},
        ),
    ]


SAMPLE_DOCUMENTS: list[dict] = [
    {
        "key": "medical_report",
        "file_hint": ["medical", "report", "hospital", "diagnosis", "priya"],
        "ocr_text": (
            "SHRI SAI CHARITABLE HOSPITAL TRUST\n"
            "Oncology Department  |  Patient Medical Summary\n"
            "----------------------------------------------\n"
            "Patient Name : Priya Sharma\n"
            "Age / Sex    : 62 / Female\n"
            "Address      : Nagpur, Maharashtra\n"
            "Aadhaar No.  : 4821 7734 9902\n"
            "Diagnosis    : Stage II Breast Carcinoma (Malignant)\n"
            "Advised      : Chemotherapy cycle to begin urgently.\n"
            "Est. Annual Household Income: Rs. 1,20,000\n"
            "NOTE: Application for Rashtriya Arogya Nidhi medical grant\n"
            "must be submitted before " + _future(5) + ".\n"
            "Income certificate to be collected from Tehsildar office."
        ),
        "extraction": {
            "beneficiary_name": "Priya Sharma",
            "government_id_type": "Aadhaar",
            "government_id_number": "4821 7734 9902",
            "critical_deadlines": [
                {
                    "date": _future(5),
                    "context": "Submit Rashtriya Arogya Nidhi medical grant application",
                }
            ],
            "detected_medical_conditions": [
                "Stage II Breast Carcinoma",
                "Malignant tumor",
                "Chemotherapy required",
            ],
            "estimated_household_income": 120000,
        },
        "profile": {
            "age": 62,
            "gender": "Female",
            "state_location": "Maharashtra",
            "is_disabled": False,
        },
    },
    {
        "key": "aadhaar_scholarship",
        "file_hint": ["aadhaar", "scholarship", "student", "school", "ramesh"],
        "ocr_text": (
            "UNIQUE IDENTIFICATION AUTHORITY OF INDIA\n"
            "Government of India\n"
            "-------------------------------------------\n"
            "Name: Aarav Kumar\n"
            "DOB: 14/03/2010   Gender: Male\n"
            "Aadhaar: 7712 3390 5561\n"
            "Address: Sitapur, Uttar Pradesh\n\n"
            "[Attached note from parent]\n"
            "Please help apply for the Post-Matric Scholarship.\n"
            "Family income around 90,000 per year.\n"
            "Last date for scholarship form is " + _future(12) + "."
        ),
        "extraction": {
            "beneficiary_name": "Aarav Kumar",
            "government_id_type": "Aadhaar",
            "government_id_number": "7712 3390 5561",
            "critical_deadlines": [
                {
                    "date": _future(12),
                    "context": "Submit Post-Matric Scholarship application form",
                }
            ],
            "detected_medical_conditions": [],
            "estimated_household_income": 90000,
        },
        "profile": {
            "age": 15,
            "gender": "Male",
            "state_location": "Uttar Pradesh",
            "is_disabled": False,
        },
    },
    {
        "key": "disability_pension",
        "file_hint": ["disability", "pension", "certificate", "handicap"],
        "ocr_text": (
            "OFFICE OF THE CHIEF MEDICAL OFFICER\n"
            "Disability Certificate (PwD)\n"
            "-------------------------------------------\n"
            "Name        : Lakshmi Devi\n"
            "Age         : 68  Gender: Female\n"
            "State       : Tamil Nadu\n"
            "Ration Card : TN-04-882317\n"
            "Disability  : Locomotor disability 55% (permanent)\n"
            "Remarks     : Eligible for state disability pension.\n"
            "Annual family income declared: Rs. 72,000\n"
            "Renewal of pension application due by " + _future(2) + "."
        ),
        "extraction": {
            "beneficiary_name": "Lakshmi Devi",
            "government_id_type": "Ration Card",
            "government_id_number": "TN-04-882317",
            "critical_deadlines": [
                {
                    "date": _future(2),
                    "context": "Renew state disability pension application",
                }
            ],
            "detected_medical_conditions": ["Locomotor disability (55%)"],
            "estimated_household_income": 72000,
        },
        "profile": {
            "age": 68,
            "gender": "Female",
            "state_location": "Tamil Nadu",
            "is_disabled": True,
        },
    },
    {
        "key": "income_certificate",
        "file_hint": ["income", "certificate", "tehsildar", "widow"],
        "ocr_text": (
            "GOVERNMENT OF RAJASTHAN\n"
            "Income Certificate\n"
            "-------------------------------------------\n"
            "This is to certify that Smt. Sunita Meena\n"
            "W/o Late Shri Ram Meena, resident of Kota, Rajasthan,\n"
            "PAN: BXYPS4412K\n"
            "has an annual household income of Rs. 48,000 only.\n"
            "Widow with two school-going children.\n"
            "Purpose: National Family Benefit Scheme application.\n"
            "Document to be submitted before " + _future(20) + "."
        ),
        "extraction": {
            "beneficiary_name": "Sunita Meena",
            "government_id_type": "PAN",
            "government_id_number": "BXYPS4412K",
            "critical_deadlines": [
                {
                    "date": _future(20),
                    "context": "Submit National Family Benefit Scheme application",
                }
            ],
            "detected_medical_conditions": [],
            "estimated_household_income": 48000,
        },
        "profile": {
            "age": 39,
            "gender": "Female",
            "state_location": "Rajasthan",
            "is_disabled": False,
            "is_bereaved": True,
        },
    },
    {
        "key": "dialysis_case",
        "file_hint": ["dialysis", "kidney", "renal", "urgent"],
        "ocr_text": (
            "CITY GENERAL HOSPITAL — NEPHROLOGY\n"
            "Treatment Advice Slip\n"
            "-------------------------------------------\n"
            "Patient: Mohammed Irfan   Age: 47   Male\n"
            "Voter ID: KAR2299871\n"
            "State: Karnataka\n"
            "Diagnosis: Chronic Kidney Disease — Stage 5 (Renal Failure)\n"
            "Advised: Twice-weekly dialysis, ongoing.\n"
            "Monthly household income approx Rs. 11,000 (~1,32,000/yr).\n"
            "URGENT: Apply for state dialysis assistance fund by "
            + _future(1) + "."
        ),
        "extraction": {
            "beneficiary_name": "Mohammed Irfan",
            "government_id_type": "Voter ID",
            "government_id_number": "KAR2299871",
            "critical_deadlines": [
                {
                    "date": _future(1),
                    "context": "Apply for state dialysis assistance fund",
                }
            ],
            "detected_medical_conditions": [
                "Chronic Kidney Disease Stage 5",
                "Renal failure",
                "Dialysis required",
            ],
            "estimated_household_income": 132000,
        },
        "profile": {
            "age": 47,
            "gender": "Male",
            "state_location": "Karnataka",
            "is_disabled": False,
        },
    },
    # ----------------------------------------------------------------------- #
    # Synthetic Aadhaar cards — SEVEN beneficiary archetypes.
    #
    # Every identity here is fabricated: the names are invented and the Aadhaar
    # numbers are randomly generated (they satisfy the Verhoeff checksum so the
    # verification panel exercises its real code path, but they are issued to
    # nobody). No real person's data appears anywhere in this file.
    #
    # Each card carries the NGO field-record footer a caseworker staples to an
    # intake, so household income and occupation remain traceable to visible
    # transcript text rather than being invented downstream.
    # ----------------------------------------------------------------------- #
    *_aadhaar_samples(),
]


def pick_sample(seed: int) -> dict:
    """Deterministically choose a sample document from an integer seed."""
    return SAMPLE_DOCUMENTS[seed % len(SAMPLE_DOCUMENTS)]


def match_sample_by_filename(filename: str) -> dict | None:
    """Pick the sample whose hint matches the filename most specifically.

    Longest match wins rather than first match: a broad hint like "aadhaar"
    would otherwise shadow every "aadhaar_<archetype>.png" sample that follows it.
    """
    lower = (filename or "").lower()
    best: tuple[int, dict] | None = None
    for sample in SAMPLE_DOCUMENTS:
        for hint in sample["file_hint"]:
            if hint in lower and (best is None or len(hint) > best[0]):
                best = (len(hint), sample)
    return best[1] if best else None
