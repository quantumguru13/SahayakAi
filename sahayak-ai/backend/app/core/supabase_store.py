"""Supabase-backed persistence — same interface as the in-memory DataStore.

Selected automatically (see store._build_store) when SUPABASE_URL + service key
are configured. Rows are scoped to a single organisation (settings.default_org_id),
matching the PRD's "single organization tenant layer". The backend uses the service
key (trusted) and enforces org scoping in every query.

Never persists a raw government ID: only a masked value + a dedup hash are stored.
Schemes (shared reference data, incl. pgvector embeddings) are loaded once and cached.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import date, datetime, timezone

from app.core import recommender
from app.core.config import settings
from app.core.pii import gov_hash, mask_id
from app.core.urgency import assess_urgency
from app.models.schemas import (
    Beneficiary,
    BeneficiaryCreate,
    DashboardMetrics,
    Document,
    ExtractedDocument,
    GovernmentIdType,
    PriorityLevel,
    SchemeMatch,
    Task,
    TaskStatus,
    UrgencyAssessment,
    WelfareScheme,
)

log = logging.getLogger("sahayak.store")

_PRIORITY_ORDER = {
    PriorityLevel.CRITICAL: 0,
    PriorityLevel.HIGH: 1,
    PriorityLevel.MEDIUM: 2,
    PriorityLevel.LOW: 3,
}


def _parse_vector(value) -> list[float]:
    if not value:
        return []
    if isinstance(value, list):
        return [float(x) for x in value]
    try:
        return [float(x) for x in json.loads(value)]
    except Exception:  # noqa: BLE001
        return []


def _parse_date(value) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _parse_dt(value) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)


class SupabaseStore:
    def __init__(self) -> None:
        from supabase import create_client

        self.org_id = settings.default_org_id
        self.client = create_client(
            settings.supabase_url, settings.supabase_service_key
        )
        # Connectivity check + scheme cache warm-up (raises -> factory falls back).
        self._schemes: dict[str, WelfareScheme] = {}
        self._scheme_rules: dict[str, dict] = {}
        self._scheme_vectors: dict[str, list[float]] = {}
        self._load_schemes()

    # -------------------------------------------------------------- schemes
    def _load_schemes(self) -> None:
        res = (
            self.client.table("welfare_schemes")
            .select(
                "id,title,description,eligibility_criteria_summary,category,"
                "eligibility_rules,scheme_vector_embedding,created_at"
            )
            .execute()
        )
        for row in res.data or []:
            scheme = WelfareScheme(
                id=str(row["id"]),
                title=row["title"],
                description=row["description"],
                eligibility_criteria_summary=row.get("eligibility_criteria_summary")
                or "",
                category=row.get("category") or "General",
                created_at=_parse_dt(row.get("created_at")),
            )
            self._schemes[scheme.id] = scheme
            self._scheme_rules[scheme.id] = row.get("eligibility_rules") or {}
            self._scheme_vectors[scheme.id] = _parse_vector(
                row.get("scheme_vector_embedding")
            )

    def list_schemes(self) -> list[WelfareScheme]:
        return list(self._schemes.values())

    def recommend_schemes(
        self, beneficiary: Beneficiary, top_k: int = 6
    ) -> list[SchemeMatch]:
        return recommender.recommend(
            beneficiary,
            list(self._schemes.values()),
            self._scheme_rules,
            self._scheme_vectors,
            top_k,
        )

    # --------------------------------------------------------- beneficiaries
    def _row_to_beneficiary(self, row: dict) -> Beneficiary:
        urgency = None
        u = row.get("urgency")
        if u:
            urgency = UrgencyAssessment.model_validate(u)
        gid = row.get("government_id_type")
        return Beneficiary(
            id=str(row["id"]),
            name=row["name"],
            age=row.get("age"),
            gender=row.get("gender"),
            annual_income=row.get("annual_income"),
            state_location=row.get("state_location"),
            is_disabled=bool(row.get("is_disabled", False)),
            government_id_type=GovernmentIdType(gid) if gid else None,
            government_id_number_masked=row.get("government_id_masked"),
            medical_conditions=row.get("medical_conditions") or [],
            current_priority=PriorityLevel(row.get("current_priority") or "MEDIUM"),
            urgency=urgency,
            created_at=_parse_dt(row.get("created_at")),
        )

    def _beneficiary_row(
        self, ben: Beneficiary, gov_hash_value: str | None
    ) -> dict:
        return {
            "id": ben.id,
            "org_id": self.org_id,
            "name": ben.name,
            "age": ben.age,
            "gender": ben.gender,
            "annual_income": ben.annual_income,
            "state_location": ben.state_location,
            "is_disabled": ben.is_disabled,
            "government_id_type": (
                ben.government_id_type.value
                if isinstance(ben.government_id_type, GovernmentIdType)
                else ben.government_id_type
            ),
            "government_id_masked": ben.government_id_number_masked,
            "government_id_hash": gov_hash_value,
            "medical_conditions": ben.medical_conditions,
            "current_priority": ben.current_priority.value,
            "urgency": ben.urgency.model_dump() if ben.urgency else None,
            "created_at": ben.created_at.isoformat(),
        }

    def list_beneficiaries(self) -> list[Beneficiary]:
        res = (
            self.client.table("beneficiaries")
            .select("*")
            .eq("org_id", self.org_id)
            .execute()
        )
        items = [self._row_to_beneficiary(r) for r in (res.data or [])]
        items.sort(
            key=lambda b: (
                _PRIORITY_ORDER.get(b.current_priority, 9),
                -(b.urgency.score if b.urgency else 0),
            )
        )
        return items

    def get_beneficiary(self, beneficiary_id: str) -> Beneficiary | None:
        res = (
            self.client.table("beneficiaries")
            .select("*")
            .eq("org_id", self.org_id)
            .eq("id", beneficiary_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return self._row_to_beneficiary(rows[0]) if rows else None

    def create_beneficiary(self, payload: BeneficiaryCreate) -> Beneficiary:
        urgency = assess_urgency(
            annual_income=payload.annual_income,
            is_disabled=payload.is_disabled,
            age=payload.age,
        )
        ben = Beneficiary(
            id=f"ben-{uuid.uuid4().hex[:8]}",
            name=payload.name,
            age=payload.age,
            gender=payload.gender,
            annual_income=payload.annual_income,
            state_location=payload.state_location,
            is_disabled=payload.is_disabled,
            current_priority=PriorityLevel(urgency.priority),
            urgency=urgency,
            created_at=datetime.now(timezone.utc),
        )
        self.client.table("beneficiaries").insert(
            self._beneficiary_row(ben, None)
        ).execute()
        return ben

    def upsert_from_extraction(
        self, extraction: ExtractedDocument, urgency: UrgencyAssessment
    ) -> Beneficiary:
        gid_type = extraction.government_id_type
        gnum = extraction.government_id_number
        ghash = gov_hash(gnum)

        existing = None
        if ghash:
            res = (
                self.client.table("beneficiaries")
                .select("*")
                .eq("org_id", self.org_id)
                .eq("government_id_hash", ghash)
                .limit(1)
                .execute()
            )
            rows = res.data or []
            existing = self._row_to_beneficiary(rows[0]) if rows else None

        if existing:
            if extraction.beneficiary_name:
                existing.name = extraction.beneficiary_name
            if extraction.age is not None:
                existing.age = extraction.age
            if extraction.gender:
                existing.gender = extraction.gender
            if extraction.estimated_household_income is not None:
                existing.annual_income = extraction.estimated_household_income
            if extraction.state_location:
                existing.state_location = extraction.state_location
            existing.is_disabled = existing.is_disabled or extraction.is_disabled
            if gid_type:
                existing.government_id_type = GovernmentIdType(gid_type)
            if gnum:
                existing.government_id_number_masked = mask_id(gnum)
            existing.medical_conditions = list(
                dict.fromkeys(
                    [*existing.medical_conditions, *extraction.detected_medical_conditions]
                )
            )
            existing.current_priority = PriorityLevel(urgency.priority)
            existing.urgency = urgency
            self.client.table("beneficiaries").update(
                self._beneficiary_row(existing, ghash)
            ).eq("id", existing.id).eq("org_id", self.org_id).execute()
            return existing

        ben = Beneficiary(
            id=f"ben-{uuid.uuid4().hex[:8]}",
            name=extraction.beneficiary_name or "Unnamed Beneficiary",
            age=extraction.age,
            gender=extraction.gender,
            annual_income=extraction.estimated_household_income,
            state_location=extraction.state_location,
            is_disabled=extraction.is_disabled,
            government_id_type=GovernmentIdType(gid_type) if gid_type else None,
            government_id_number_masked=mask_id(gnum),
            medical_conditions=extraction.detected_medical_conditions,
            current_priority=PriorityLevel(urgency.priority),
            urgency=urgency,
            created_at=datetime.now(timezone.utc),
        )
        self.client.table("beneficiaries").insert(
            self._beneficiary_row(ben, ghash)
        ).execute()
        return ben

    # ------------------------------------------------------------- documents
    def add_document(
        self, beneficiary_id: str, file_name: str, extracted_text: str,
        parsed: ExtractedDocument,
    ) -> Document:
        # Never persist the raw government ID inside parsed_metadata.
        safe_meta = parsed.model_copy(
            update={"government_id_number": mask_id(parsed.government_id_number)}
        )
        doc = Document(
            id=f"doc-{uuid.uuid4().hex[:8]}",
            beneficiary_id=beneficiary_id,
            file_name=file_name,
            file_url=f"supabase://documents/{file_name}",
            extracted_text=extracted_text,
            parsed_metadata=safe_meta,
            created_at=datetime.now(timezone.utc),
        )
        self.client.table("documents").insert(
            {
                "id": doc.id,
                "org_id": self.org_id,
                "beneficiary_id": beneficiary_id,
                "file_name": file_name,
                "file_url": doc.file_url,
                "extracted_text": extracted_text,
                "parsed_metadata": safe_meta.model_dump(),
                "created_at": doc.created_at.isoformat(),
            }
        ).execute()
        return doc

    # ----------------------------------------------------------------- tasks
    def _row_to_task(self, row: dict) -> Task:
        return Task(
            id=str(row["id"]),
            beneficiary_id=str(row["beneficiary_id"]),
            title=row["title"],
            description=row.get("description"),
            due_date=_parse_date(row.get("due_date")),
            status=TaskStatus(row.get("status") or "PENDING"),
            created_at=_parse_dt(row.get("created_at")),
        )

    def list_tasks(self, beneficiary_id: str | None = None) -> list[Task]:
        q = (
            self.client.table("tasks")
            .select("*")
            .eq("org_id", self.org_id)
        )
        if beneficiary_id:
            q = q.eq("beneficiary_id", beneficiary_id)
        res = q.execute()
        items = [self._row_to_task(r) for r in (res.data or [])]
        items.sort(key=lambda t: (t.due_date or date.max, t.created_at))
        return items

    def _make_task(
        self, beneficiary_id: str, title: str, description: str | None,
        due_date: date | None,
    ) -> Task:
        task = Task(
            id=f"task-{uuid.uuid4().hex[:8]}",
            beneficiary_id=beneficiary_id,
            title=title,
            description=description,
            due_date=due_date,
            status=TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        self.client.table("tasks").insert(
            {
                "id": task.id,
                "org_id": self.org_id,
                "beneficiary_id": beneficiary_id,
                "title": title,
                "description": description,
                "due_date": due_date.isoformat() if due_date else None,
                "status": task.status.value,
                "created_at": task.created_at.isoformat(),
            }
        ).execute()
        return task

    def add_tasks_from_extraction(
        self, beneficiary_id: str, extraction: ExtractedDocument
    ) -> list[Task]:
        created: list[Task] = []
        for dl in extraction.critical_deadlines:
            created.append(
                self._make_task(
                    beneficiary_id,
                    title=dl.context or "Follow up on application deadline",
                    description=f"Auto-generated from uploaded document (due {dl.date}).",
                    due_date=_parse_date(dl.date),
                )
            )
        if extraction.estimated_household_income is not None:
            created.append(
                self._make_task(
                    beneficiary_id,
                    title="Collect / verify income certificate",
                    description="Required to substantiate estimated household income.",
                    due_date=None,
                )
            )
        if extraction.detected_medical_conditions:
            created.append(
                self._make_task(
                    beneficiary_id,
                    title="Attach latest medical diagnosis report",
                    description="Supports medical-aid scheme eligibility.",
                    due_date=None,
                )
            )
        return created

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task | None:
        res = (
            self.client.table("tasks")
            .update({"status": status.value})
            .eq("id", task_id)
            .eq("org_id", self.org_id)
            .execute()
        )
        rows = res.data or []
        return self._row_to_task(rows[0]) if rows else None

    # ------------------------------------------------------------- dashboard
    def metrics(self) -> DashboardMetrics:
        bens = self.list_beneficiaries()
        tasks = self.list_tasks()
        today = date.today()
        return DashboardMetrics(
            total_beneficiaries=len(bens),
            critical_cases=sum(
                1 for b in bens if b.current_priority == PriorityLevel.CRITICAL
            ),
            high_cases=sum(
                1 for b in bens if b.current_priority == PriorityLevel.HIGH
            ),
            pending_tasks=sum(1 for t in tasks if t.status != TaskStatus.COMPLETED),
            overdue_tasks=sum(
                1
                for t in tasks
                if t.status != TaskStatus.COMPLETED
                and t.due_date is not None
                and t.due_date < today
            ),
            schemes_available=len(self._schemes),
        )

    def reset(self) -> None:
        from app.models.schemas import Beneficiary, PriorityLevel, TaskStatus, CriticalDeadline, GovernmentIdType
        from app.core.urgency import assess_urgency
        from app.core.pii import _gov_hash, _mask_id
        from app.data import seed

        # Delete org-scoped tasks, documents, and beneficiaries
        self.client.table("tasks").delete().eq("org_id", self.org_id).execute()
        self.client.table("documents").delete().eq("org_id", self.org_id).execute()
        self.client.table("beneficiaries").delete().eq("org_id", self.org_id).execute()
        
        # Reload schemes to make sure we're clean
        self._load_schemes()
        
        # Seed beneficiaries
        for b in seed.BENEFICIARIES:
            deadlines = [CriticalDeadline(**b["deadline"])] if b.get("deadline") else []
            urgency = assess_urgency(
                medical_conditions=b.get("medical_conditions", []),
                deadlines=deadlines,
                annual_income=b.get("annual_income"),
                is_disabled=b.get("is_disabled", False),
                age=b.get("age"),
            )
            ben = Beneficiary(
                id=b["id"],
                name=b["name"],
                age=b.get("age"),
                gender=b.get("gender"),
                annual_income=b.get("annual_income"),
                state_location=b.get("state_location"),
                is_disabled=b.get("is_disabled", False),
                government_id_type=GovernmentIdType(b.get("government_id_type")) if b.get("government_id_type") else None,
                government_id_number_masked=_mask_id(b.get("government_id_number")),
                medical_conditions=b.get("medical_conditions", []),
                current_priority=PriorityLevel(urgency.priority),
                urgency=urgency,
                created_at=b["created_at"],
            )
            self.client.table("beneficiaries").insert(
                self._beneficiary_row(ben, _gov_hash(b.get("government_id_number")))
            ).execute()
            
        # Seed tasks
        for t in seed.TASKS:
            due = t.get("due_date")
            self.client.table("tasks").insert(
                {
                    "id": t["id"],
                    "org_id": self.org_id,
                    "beneficiary_id": t["beneficiary_id"],
                    "title": t["title"],
                    "description": t.get("description"),
                    "due_date": due.isoformat() if due else None,
                    "status": t["status"],
                }
            ).execute()
