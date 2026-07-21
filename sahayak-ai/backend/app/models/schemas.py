"""Pydantic v2 models — strict schemas for the Sahayak AI document-intelligence pipeline.

These models are the single source of truth for the shapes flowing between the
OCR/LLM extraction layer, the urgency matrix, the semantic recommender and the API.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# --------------------------------------------------------------------------- #
# Enumerations (mirror the PostgreSQL ENUM types in supabase/schema.sql)
# --------------------------------------------------------------------------- #
class PriorityLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"


class GovernmentIdType(str, Enum):
    AADHAAR = "Aadhaar"
    PAN = "PAN"
    RATION_CARD = "Ration Card"
    VOTER_ID = "Voter ID"


# --------------------------------------------------------------------------- #
# Extraction schema — the EXACT JSON contract GPT-4o must return (temp=0.1)
# --------------------------------------------------------------------------- #
class CriticalDeadline(BaseModel):
    date: str = Field(..., description="ISO date YYYY-MM-DD")
    context: str = Field(..., description="What the deadline is for")


class ExtractedDocument(BaseModel):
    """Strict contract matching the PRD prompt-engineering schema."""

    model_config = ConfigDict(use_enum_values=True)

    beneficiary_name: Optional[str] = None
    government_id_type: Optional[GovernmentIdType] = None
    government_id_number: Optional[str] = None
    critical_deadlines: list[CriticalDeadline] = Field(default_factory=list)
    detected_medical_conditions: list[str] = Field(default_factory=list)
    estimated_household_income: Optional[float] = None
    # Extended profile fields — improve urgency scoring + scheme matching in LIVE
    # mode (where age/gender/state are otherwise unavailable to the recommender).
    age: Optional[int] = None
    gender: Optional[str] = None
    state_location: Optional[str] = None
    is_disabled: bool = False
    # Death of the primary breadwinner / widowhood. This is the triggering life
    # event for NFBS, so without it that scheme cannot be sensibly recommended.
    is_bereaved: bool = False
    # Livelihood — drives occupation-linked schemes (e.g. PM-KISAN for farmers).
    occupation: Optional[str] = None
    # Raw identity fields surfaced by the real OCR extractor (LIVE mode).
    dob: Optional[str] = None
    address: Optional[str] = None


# --------------------------------------------------------------------------- #
# Urgency matrix output
# --------------------------------------------------------------------------- #
class UrgencyAssessment(BaseModel):
    priority: PriorityLevel
    score: int = Field(..., ge=0, le=100)
    reasoning: str
    medical_severity: int = Field(..., ge=0, le=100)
    deadline_pressure: int = Field(..., ge=0, le=100)


# --------------------------------------------------------------------------- #
# Core entities
# --------------------------------------------------------------------------- #
class Task(BaseModel):
    id: str
    beneficiary_id: str
    title: str
    description: Optional[str] = None
    due_date: Optional[date] = None
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime


class Document(BaseModel):
    id: str
    beneficiary_id: str
    file_name: str
    file_url: str
    extracted_text: Optional[str] = None
    parsed_metadata: Optional[ExtractedDocument] = None
    created_at: datetime


class Beneficiary(BaseModel):
    id: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    annual_income: Optional[float] = None
    state_location: Optional[str] = None
    is_disabled: bool = False
    is_bereaved: bool = False
    occupation: Optional[str] = None
    government_id_type: Optional[GovernmentIdType] = None
    government_id_number_masked: Optional[str] = None
    medical_conditions: list[str] = Field(default_factory=list)
    current_priority: PriorityLevel = PriorityLevel.MEDIUM
    urgency: Optional[UrgencyAssessment] = None
    created_at: datetime
    # Provenance — "seed"/"demo" (sample data) or "live" (real OCR upload).
    # Lets the dashboard show ONLY live cases in LIVE mode (no demo leakage).
    source: str = "live"


# --------------------------------------------------------------------------- #
# Welfare schemes + recommendations
# --------------------------------------------------------------------------- #
class WelfareScheme(BaseModel):
    id: str
    title: str
    description: str
    eligibility_criteria_summary: str
    category: str
    created_at: datetime


class SchemeMatch(BaseModel):
    scheme: WelfareScheme
    confidence: float = Field(..., ge=0, le=1, description="Eligibility confidence 0-1")
    semantic_similarity: float = Field(..., ge=0, le=1)
    rule_score: float = Field(..., ge=0, le=1)
    matched_reasons: list[str] = Field(default_factory=list)
    is_alternative: bool = False


# --------------------------------------------------------------------------- #
# Dashboard / brief
# --------------------------------------------------------------------------- #
class DashboardMetrics(BaseModel):
    total_beneficiaries: int
    critical_cases: int
    high_cases: int
    pending_tasks: int
    overdue_tasks: int
    schemes_available: int


class BriefAction(BaseModel):
    beneficiary_id: Optional[str] = None
    beneficiary_name: Optional[str] = None
    action: str
    reason: str
    priority: PriorityLevel


class DailyBrief(BaseModel):
    generated_at: datetime
    headline: str
    summary_markdown: str
    top_actions: list[BriefAction]
    metrics: DashboardMetrics
    system_healthy: bool


# --------------------------------------------------------------------------- #
# Request / response payloads
# --------------------------------------------------------------------------- #
class BeneficiaryCreate(BaseModel):
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    annual_income: Optional[float] = None
    state_location: Optional[str] = None
    is_disabled: bool = False


class PipelineMode(str, Enum):
    LIVE = "LIVE"
    DEMO = "DEMO"


class PipelineDebug(BaseModel):
    """Diagnostics for the judge-facing debug panel + status chips."""

    mode: PipelineMode
    ocr_engine: str                     # e.g. "tesseract", "easyocr", "gpt-4o-vision", "pdf-text", "sample"
    ocr_confidence: float = Field(..., ge=0, le=1)
    extraction_confidence: float = Field(..., ge=0, le=1)
    ai_status: str                      # "ok" | "fallback" | "sample"
    scheme_matching_status: str         # "ok" | "none"
    engines_attempted: list[str] = Field(default_factory=list)
    original_image: Optional[str] = None       # data URI
    preprocessed_image: Optional[str] = None   # data URI
    notes: list[str] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Aadhaar document intelligence
# --------------------------------------------------------------------------- #
class AadhaarSide(str, Enum):
    FRONT = "front"
    BACK = "back"
    COMBINED = "combined"
    UNKNOWN = "unknown"


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    NOT_AADHAAR = "NOT_AADHAAR"


class AadhaarFields(BaseModel):
    """Extracted Aadhaar profile. `aadhaar_number` is ALWAYS the masked form —
    the raw value never leaves app.core.aadhaar."""

    full_name: Optional[str] = None
    aadhaar_number: Optional[str] = None  # "XXXX XXXX 1234"
    date_of_birth: Optional[str] = None
    year_of_birth: Optional[int] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    pin_code: Optional[str] = None
    mobile: Optional[str] = None
    qr_detected: bool = False
    qr_preview: Optional[str] = None
    side: AadhaarSide = AadhaarSide.UNKNOWN


class AadhaarVerification(BaseModel):
    status: VerificationStatus
    checks: dict[str, bool] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    manual_review: bool = True
    front_back_conflicts: list[str] = Field(default_factory=list)


class AadhaarAnalysis(BaseModel):
    """Everything the Aadhaar analysis panel renders."""

    fields: AadhaarFields
    verification: AadhaarVerification
    ocr_confidence: float = Field(..., ge=0, le=1)
    low_confidence: bool = False


class UploadHistoryEntry(BaseModel):
    """Audit trail row — one per upload attempt, success or failure."""

    session_id: str
    created_at: datetime
    document_type: str            # "aadhaar" | "document"
    mode: PipelineMode
    ocr_engine: str
    processing_ms: int
    status: str                   # "SUCCESS" | "OCR_UNAVAILABLE" | "REJECTED"
    verification_status: Optional[str] = None
    user_id: str
    user_role: str
    file_name: str
    beneficiary_id: Optional[str] = None


class DocumentUploadResponse(BaseModel):
    document_id: str
    beneficiary: Beneficiary
    extraction: ExtractedDocument
    urgency: UrgencyAssessment
    extracted_text: str
    processing_ms: int
    scheme_matches: list[SchemeMatch]
    generated_tasks: list[Task]
    demo_mode: bool
    # New pipeline metadata (LIVE vs DEMO, confidences, debug imagery)
    mode: PipelineMode = PipelineMode.DEMO
    debug: Optional[PipelineDebug] = None
    # Present only when the upload was recognised as an Aadhaar document.
    aadhaar: Optional[AadhaarAnalysis] = None
    # Audit correlation id — matches the UploadHistoryEntry for this upload.
    session_id: Optional[str] = None


class OcrUnavailableResponse(BaseModel):
    """Returned (HTTP 200) when LIVE OCR fails — powers the graceful fallback UI
    ('OCR unavailable — Retry OCR / Switch to Demo'). Never a crash, never fake text."""

    ocr_available: bool = False
    mode: PipelineMode = PipelineMode.LIVE
    message: str
    engines_attempted: list[str] = Field(default_factory=list)
    can_switch_to_demo: bool = True


class TaskUpdate(BaseModel):
    status: TaskStatus


class ImpactReport(BaseModel):
    generated_at: datetime
    title: str
    period: str
    markdown: str
    stats: dict


class HealthResponse(BaseModel):
    status: str
    demo_mode: bool
    openai_configured: bool
    supabase_configured: bool
    auth_enabled: bool = False
    # Real-OCR capability so the frontend can enable/disable LIVE mode intelligently.
    default_mode: PipelineMode = PipelineMode.DEMO
    live_ocr_available: bool = False
    ocr_engines: list[str] = Field(default_factory=list)
    # The mode the dashboard is currently scoped to (togglable at runtime).
    active_mode: PipelineMode = PipelineMode.DEMO
