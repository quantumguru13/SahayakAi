"""Seed corpus: real Indian welfare schemes + demonstration beneficiaries & tasks.

Welfare schemes carry BOTH a natural-language description (embedded into a 1536-dim
vector for semantic cosine matching) AND structured eligibility rules (used by the
deterministic rule-scorer). Live mode blends real embeddings + rules; demo mode
leans on rules + keyword similarity. Either way, confidence scores stay sensible.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone


def _dt(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def _due(days: int) -> date:
    return date.today() + timedelta(days=days)


# --------------------------------------------------------------------------- #
# Welfare schemes (rules power the deterministic eligibility scorer)
# --------------------------------------------------------------------------- #
WELFARE_SCHEMES: list[dict] = [
    {
        "id": "scheme-ran",
        "title": "Rashtriya Arogya Nidhi (RAN)",
        "category": "Medical",
        "description": (
            "Financial assistance to patients living below the poverty line who are "
            "suffering from major life-threatening diseases such as cancer, kidney "
            "failure, and heart conditions, to receive treatment at government hospitals."
        ),
        "eligibility_criteria_summary": (
            "BPL households; life-threatening illness (cancer, renal, cardiac); "
            "treatment at government / recognised hospital."
        ),
        "rules": {
            "max_income": 150000,
            # RAN funds treatment for major life-threatening illness — without such
            # a diagnosis on file it must not be recommended at all.
            "requires_medical_match": True,
            "medical_keywords": [
                "cancer", "carcinoma", "tumor", "malignant", "renal", "kidney",
                "dialysis", "cardiac", "heart", "transplant", "leukemia",
            ],
        },
    },
    {
        "id": "scheme-pmjay",
        "title": "Ayushman Bharat PM-JAY",
        "category": "Medical",
        "description": (
            "Provides health cover of up to five lakh rupees per family per year for "
            "secondary and tertiary care hospitalisation to poor and vulnerable "
            "families across India."
        ),
        "eligibility_criteria_summary": (
            "Economically weaker families; covers hospitalisation for a wide range of "
            "medical and surgical conditions."
        ),
        "rules": {
            "max_income": 250000,
            "medical_keywords": [
                "cancer", "renal", "kidney", "dialysis", "surgery", "cardiac",
                "chemotherapy", "hospitalisation", "carcinoma", "chronic",
                "anemia", "anaemia", "thalassemia", "hepatitis", "tuberculosis",
                "fracture", "pneumonia", "sepsis", "stroke", "diabetes",
            ],
        },
    },
    {
        "id": "scheme-pmndp",
        "title": "Pradhan Mantri National Dialysis Programme",
        "category": "Medical",
        "description": (
            "Free dialysis services for poor patients suffering from chronic kidney "
            "disease and end-stage renal failure at district hospitals."
        ),
        "eligibility_criteria_summary": (
            "Chronic kidney disease / renal failure patients requiring dialysis; "
            "priority to low-income households."
        ),
        "rules": {
            "max_income": 200000,
            # A dialysis programme is meaningless without a renal diagnosis.
            "requires_medical_match": True,
            "medical_keywords": ["kidney", "renal", "dialysis", "nephrology", "ckd"],
        },
    },
    {
        "id": "scheme-nfbs",
        "title": "National Family Benefit Scheme (NFBS)",
        "category": "Social Security",
        "description": (
            "A one-time lump-sum family benefit to below-poverty-line households upon "
            "the death of the primary breadwinner, supporting bereaved families "
            "including widows and dependent children."
        ),
        "eligibility_criteria_summary": (
            "BPL family; death of primary breadwinner; one-time relief grant."
        ),
        # NFBS is triggered by the death of the primary breadwinner. Without that
        # event it must not be recommended — an income ceiling alone previously made
        # it the top match for every low-income case, including a plain Aadhaar card.
        "rules": {
            "max_income": 100000,
            "requires_bereavement": True,
            "keywords": ["widow", "family", "breadwinner"],
        },
    },
    {
        "id": "scheme-postmatric",
        "title": "Post-Matric Scholarship (SC/ST/OBC)",
        "category": "Education",
        "description": (
            "Scholarships for students from scheduled castes, tribes and other "
            "backward classes studying at post-matriculation levels to cover tuition "
            "and maintenance, reducing school and college dropout."
        ),
        "eligibility_criteria_summary": (
            "Students in classes 11+ / college; family income under 2.5 lakh; covers "
            "tuition and maintenance allowance."
        ),
        "rules": {
            "min_age": 13,
            "max_age": 25,
            "max_income": 250000,
            "keywords": ["scholarship", "student", "school", "college", "education"],
        },
    },
    {
        "id": "scheme-prematric",
        "title": "Pre-Matric Scholarship",
        "category": "Education",
        "description": (
            "Financial support for school-going children up to class 10 from "
            "economically weaker sections to cover books, uniforms and fees."
        ),
        "eligibility_criteria_summary": (
            "School children up to class 10; low-income family; covers books and fees."
        ),
        "rules": {
            "min_age": 5,
            "max_age": 16,
            "max_income": 200000,
            "keywords": ["scholarship", "student", "school", "education", "child"],
        },
    },
    {
        "id": "scheme-disability-pension",
        "title": "Indira Gandhi National Disability Pension Scheme",
        "category": "Pension",
        "description": (
            "Monthly pension to persons with severe or multiple disabilities from "
            "below-poverty-line households to support their livelihood and care."
        ),
        "eligibility_criteria_summary": (
            "Age 18-79; severe disability (40%+); BPL household."
        ),
        "rules": {
            "min_age": 18,
            "max_age": 79,
            "max_income": 100000,
            "requires_disability": True,
            "medical_keywords": ["disability", "disabled", "locomotor", "blind"],
        },
    },
    {
        "id": "scheme-oldage-pension",
        "title": "Indira Gandhi National Old Age Pension Scheme",
        "category": "Pension",
        "description": (
            "Monthly old-age pension for senior citizens aged sixty years and above "
            "belonging to below-poverty-line families."
        ),
        "eligibility_criteria_summary": "Age 60+; below-poverty-line household.",
        "rules": {"min_age": 60, "max_income": 100000, "keywords": ["senior", "elderly"]},
    },
    {
        "id": "scheme-widow-pension",
        "title": "Indira Gandhi National Widow Pension Scheme",
        "category": "Pension",
        "description": (
            "Monthly pension to widows aged forty to fifty-nine years from "
            "below-poverty-line households to provide social security."
        ),
        "eligibility_criteria_summary": "Widows aged 40-59; BPL household.",
        "rules": {
            "min_age": 40,
            "max_age": 59,
            "max_income": 100000,
            "gender": "Female",
            "keywords": ["widow"],
        },
    },
    {
        "id": "scheme-cm-relief",
        "title": "Chief Minister's Relief Fund (Medical Aid)",
        "category": "Medical",
        "description": (
            "Discretionary state medical and disaster relief assistance for citizens "
            "facing acute financial distress from illness or emergencies not fully "
            "covered by other central schemes. A general-purpose safety net."
        ),
        "eligibility_criteria_summary": (
            "Any resident in acute distress; general medical / emergency relief."
        ),
        "rules": {"max_income": 300000, "is_fallback": True},
    },
    {
        "id": "scheme-pmsym",
        "title": "PM Shram Yogi Maan-dhan (PM-SYM)",
        "category": "Livelihood",
        "description": (
            "A voluntary contributory pension for unorganised-sector workers such as "
            "daily-wage labourers, domestic workers, street vendors and rickshaw "
            "pullers, assuring three thousand rupees a month after the age of sixty."
        ),
        "eligibility_criteria_summary": (
            "Unorganised-sector worker aged 18-40; monthly income up to ₹15,000; "
            "not covered by EPFO/ESIC."
        ),
        "rules": {
            "min_age": 18,
            "max_age": 40,
            "max_income": 180000,
            "occupations": [
                "labourer", "daily wage", "domestic worker", "weaver",
                "fisherman", "vendor", "worker",
            ],
            "keywords": ["pension", "unorganised", "worker"],
        },
    },
    {
        "id": "scheme-pmkisan",
        "title": "PM-KISAN Samman Nidhi",
        "category": "Livelihood",
        "description": (
            "Income support of six thousand rupees per year, paid in three equal "
            "instalments, to land-holding farmer families to meet agricultural "
            "input costs and household needs."
        ),
        "eligibility_criteria_summary": (
            "Land-holding farmer families; small and marginal cultivators; "
            "paid directly to the beneficiary's bank account."
        ),
        "rules": {
            "max_income": 200000,
            # Livelihood scheme — only meaningful for a cultivator.
            "occupations": ["farmer", "kisan", "cultivator", "agricultur"],
            "keywords": ["farmer", "agriculture", "land"],
        },
    },
]


# --------------------------------------------------------------------------- #
# Demonstration beneficiaries (populate the dashboard so it looks alive)
# --------------------------------------------------------------------------- #
BENEFICIARIES: list[dict] = [
    {
        "id": "ben-001",
        "name": "Priya Sharma",
        "age": 62,
        "gender": "Female",
        "annual_income": 120000,
        "state_location": "Maharashtra",
        "is_disabled": False,
        "government_id_type": "Aadhaar",
        "government_id_number": "4821 7734 9902",
        "medical_conditions": ["Stage II Breast Carcinoma", "Malignant tumor"],
        "deadline": {"date": _due(5).isoformat(), "context": "RAN medical grant"},
        "created_at": _dt(9),
    },
    {
        "id": "ben-002",
        "name": "Mohammed Irfan",
        "age": 47,
        "gender": "Male",
        "annual_income": 132000,
        "state_location": "Karnataka",
        "is_disabled": False,
        "government_id_type": "Voter ID",
        "government_id_number": "KAR2299871",
        "medical_conditions": ["Chronic Kidney Disease Stage 5", "Renal failure"],
        "deadline": {"date": _due(1).isoformat(), "context": "Dialysis assistance fund"},
        "created_at": _dt(4),
    },
    {
        "id": "ben-003",
        "name": "Lakshmi Devi",
        "age": 68,
        "gender": "Female",
        "annual_income": 72000,
        "state_location": "Tamil Nadu",
        "is_disabled": True,
        "government_id_type": "Ration Card",
        "government_id_number": "TN-04-882317",
        "medical_conditions": ["Locomotor disability (55%)"],
        "deadline": {"date": _due(2).isoformat(), "context": "Disability pension renewal"},
        "created_at": _dt(15),
    },
    {
        "id": "ben-004",
        "name": "Aarav Kumar",
        "age": 15,
        "gender": "Male",
        "annual_income": 90000,
        "state_location": "Uttar Pradesh",
        "is_disabled": False,
        "government_id_type": "Aadhaar",
        "government_id_number": "7712 3390 5561",
        "medical_conditions": [],
        "deadline": {"date": _due(12).isoformat(), "context": "Post-Matric Scholarship"},
        "created_at": _dt(6),
    },
    {
        "id": "ben-005",
        "name": "Sunita Meena",
        "age": 39,
        "gender": "Female",
        "annual_income": 48000,
        "state_location": "Rajasthan",
        "is_disabled": False,
        # Widow ("W/o Late Shri Ram Meena") — the NFBS triggering event.
        "is_bereaved": True,
        "government_id_type": "PAN",
        "government_id_number": "BXYPS4412K",
        "medical_conditions": [],
        "deadline": {"date": _due(20).isoformat(), "context": "NFBS application"},
        "created_at": _dt(11),
    },
    {
        "id": "ben-006",
        "name": "Ramesh Yadav",
        "age": 71,
        "gender": "Male",
        "annual_income": 60000,
        "state_location": "Bihar",
        "is_disabled": False,
        "government_id_type": "Aadhaar",
        "government_id_number": "9921 4432 1187",
        "medical_conditions": ["Hypertension"],
        "deadline": None,
        "created_at": _dt(22),
    },
]


# --------------------------------------------------------------------------- #
# Tasks / timeline (some overdue to light up the daily brief)
# --------------------------------------------------------------------------- #
TASKS: list[dict] = [
    {
        "id": "task-001",
        "beneficiary_id": "ben-001",
        "title": "Collect income certificate from Tehsildar office",
        "description": "Required for Rashtriya Arogya Nidhi medical grant application.",
        "due_date": _due(3),
        "status": "PENDING",
        "created_at": _dt(9),
    },
    {
        "id": "task-002",
        "beneficiary_id": "ben-001",
        "title": "Submit RAN medical grant application",
        "description": "Deadline critical — chemotherapy cannot begin without funds.",
        "due_date": _due(5),
        "status": "IN_PROGRESS",
        "created_at": _dt(9),
    },
    {
        "id": "task-003",
        "beneficiary_id": "ben-002",
        "title": "File state dialysis assistance fund application",
        "description": "Twice-weekly dialysis ongoing; urgent.",
        "due_date": _due(1),
        "status": "PENDING",
        "created_at": _dt(4),
    },
    {
        "id": "task-004",
        "beneficiary_id": "ben-003",
        "title": "Renew disability pension application",
        "description": "Locomotor disability certificate attached.",
        "due_date": _due(-1),  # overdue
        "status": "PENDING",
        "created_at": _dt(15),
    },
    {
        "id": "task-005",
        "beneficiary_id": "ben-004",
        "title": "Upload Aadhaar + income proof for scholarship portal",
        "description": "Post-Matric Scholarship form window closing soon.",
        "due_date": _due(12),
        "status": "PENDING",
        "created_at": _dt(6),
    },
    {
        "id": "task-006",
        "beneficiary_id": "ben-005",
        "title": "Verify widow certificate for NFBS",
        "description": None,
        "due_date": _due(18),
        "status": "PENDING",
        "created_at": _dt(11),
    },
    {
        "id": "task-007",
        "beneficiary_id": "ben-003",
        "title": "Confirm bank account seeding for pension credit",
        "description": "Aadhaar-bank linkage pending.",
        "due_date": _due(-3),  # overdue
        "status": "PENDING",
        "created_at": _dt(14),
    },
]
