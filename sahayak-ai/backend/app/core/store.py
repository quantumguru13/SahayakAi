"""In-memory data store + semantic welfare recommender.

For the hackathon MVP this runs entirely in memory (seeded, deterministic) so the
judge demo never depends on a live database. The equivalent PostgreSQL schema and
seed live in ../../supabase and are used verbatim when Supabase is provisioned;
the query shapes here mirror that schema 1:1.

The recommender blends:
  * rule_score        — deterministic eligibility rules (age/income/disability/medical)
  * semantic_similarity — cosine similarity of 1536-dim embeddings (pgvector-style)
into a single eligibility `confidence`.
"""
from __future__ import annotations

import threading
import uuid
from datetime import date, datetime, timezone

from app.core import ai_engine, recommender
from app.core.pii import gov_hash as _gov_hash
from app.core.pii import mask_id as _mask_id
from app.core.urgency import assess_urgency
from app.data import seed
from app.models.schemas import (
    Beneficiary,
    BeneficiaryCreate,
    CriticalDeadline,
    DashboardMetrics,
    Document,
    ExtractedDocument,
    GovernmentIdType,
    PriorityLevel,
    SchemeMatch,
    Task,
    TaskStatus,
    UploadHistoryEntry,
    UrgencyAssessment,
    WelfareScheme,
)

_PRIORITY_ORDER = {
    PriorityLevel.CRITICAL: 0,
    PriorityLevel.HIGH: 1,
    PriorityLevel.MEDIUM: 2,
    PriorityLevel.LOW: 3,
}


class DataStore:
    """Thread-safe singleton in-memory store."""

    def __init__(self) -> None:
        from app.core.config import settings

        self._lock = threading.RLock()
        self.beneficiaries: dict[str, Beneficiary] = {}
        self.tasks: dict[str, Task] = {}
        self.documents: dict[str, Document] = {}
        self.schemes: dict[str, WelfareScheme] = {}
        self._scheme_rules: dict[str, dict] = {}
        self._scheme_vectors: dict[str, list[float]] = {}
        self._gov_id_index: dict[str, str] = {}  # gov-id hash -> beneficiary id
        # Audit trail (newest first) + hashes of documents already ingested, so a
        # re-upload of the same file is reported rather than silently duplicated.
        self.history: list[UploadHistoryEntry] = []
        self._document_hashes: set[str] = set()
        # The mode the dashboard/lists are currently scoped to. LIVE hides all
        # seed/demo beneficiaries so real uploads are never mixed with sample data.
        self.active_mode: str = settings.default_pipeline_mode
        self._seed()

    # ---------------------------------------------------------- mode / scoping
    def set_active_mode(self, mode: str) -> str:
        m = (mode or "").strip().upper()
        if m not in ("LIVE", "DEMO"):
            m = "DEMO"
        with self._lock:
            self.active_mode = m
        return m

    def _visible_sources(self) -> set[str]:
        """Which beneficiary sources are shown in the current active mode."""
        return {"live"} if self.active_mode == "LIVE" else {"seed", "demo"}

    def _is_visible(self, b: Beneficiary) -> bool:
        return (b.source or "live") in self._visible_sources()

    # ------------------------------------------------------------------ seed
    def _seed(self) -> None:
        for s in seed.WELFARE_SCHEMES:
            scheme = WelfareScheme(
                id=s["id"],
                title=s["title"],
                description=s["description"],
                eligibility_criteria_summary=s["eligibility_criteria_summary"],
                category=s["category"],
                created_at=datetime.now(timezone.utc),
            )
            self.schemes[scheme.id] = scheme
            self._scheme_rules[scheme.id] = s["rules"]
            embed_src = f"{s['title']}. {s['description']} {s['eligibility_criteria_summary']}"
            self._scheme_vectors[scheme.id] = ai_engine.embed_text(embed_src)

        for b in seed.BENEFICIARIES:
            deadlines = (
                [CriticalDeadline(**b["deadline"])] if b.get("deadline") else []
            )
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
                is_bereaved=b.get("is_bereaved", False),
                occupation=b.get("occupation"),
                government_id_type=b.get("government_id_type"),
                government_id_number_masked=_mask_id(b.get("government_id_number")),
                medical_conditions=b.get("medical_conditions", []),
                current_priority=PriorityLevel(urgency.priority),
                urgency=urgency,
                created_at=b["created_at"],
                source="seed",
            )
            self.beneficiaries[ben.id] = ben
            ghash = _gov_hash(b.get("government_id_number"))
            if ghash:
                self._gov_id_index[ghash] = ben.id

        for t in seed.TASKS:
            task = Task(
                id=t["id"],
                beneficiary_id=t["beneficiary_id"],
                title=t["title"],
                description=t.get("description"),
                due_date=t.get("due_date"),
                status=TaskStatus(t["status"]),
                created_at=t["created_at"],
            )
            self.tasks[task.id] = task

    def reset(self) -> None:
        with self._lock:
            self.beneficiaries.clear()
            self.tasks.clear()
            self.documents.clear()
            self.schemes.clear()
            self._scheme_rules.clear()
            self._scheme_vectors.clear()
            self._gov_id_index.clear()
            self.history.clear()
            self._document_hashes.clear()
            self._seed()

    # ---------------------------------------------------------- beneficiaries
    def list_beneficiaries(self) -> list[Beneficiary]:
        with self._lock:
            items = [b for b in self.beneficiaries.values() if self._is_visible(b)]
        # Live uploads first (newest at the top), then by priority/urgency — so the
        # document a judge just uploaded is always the first thing they see.
        items.sort(
            key=lambda b: (
                _PRIORITY_ORDER.get(b.current_priority, 9),
                -(b.urgency.score if b.urgency else 0),
                -b.created_at.timestamp(),
            )
        )
        return items

    def get_beneficiary(self, beneficiary_id: str) -> Beneficiary | None:
        with self._lock:
            return self.beneficiaries.get(beneficiary_id)

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
        with self._lock:
            self.beneficiaries[ben.id] = ben
        return ben

    def upsert_from_extraction(
        self, extraction: ExtractedDocument, urgency: UrgencyAssessment,
        source: str = "live",
    ) -> Beneficiary:
        """Create — or, if the government ID matches an existing case, refresh —
        a beneficiary from a parsed document. Dedup prevents duplicate profiles
        when the same person's document is uploaded more than once.

        ``source`` tags provenance ("live" real upload vs "demo" sample) so the
        dashboard can scope what it shows to the active mode."""
        gid_type = extraction.government_id_type
        gnum = extraction.government_id_number
        ghash = _gov_hash(gnum)

        with self._lock:
            existing_id = self._gov_id_index.get(ghash) if ghash else None
            if existing_id and existing_id in self.beneficiaries:
                ben = self.beneficiaries[existing_id]
                if extraction.beneficiary_name:
                    ben.name = extraction.beneficiary_name
                if extraction.age is not None:
                    ben.age = extraction.age
                if extraction.gender:
                    ben.gender = extraction.gender
                if extraction.estimated_household_income is not None:
                    ben.annual_income = extraction.estimated_household_income
                if extraction.state_location:
                    ben.state_location = extraction.state_location
                ben.is_disabled = ben.is_disabled or extraction.is_disabled
                ben.is_bereaved = ben.is_bereaved or extraction.is_bereaved
                if extraction.occupation:
                    ben.occupation = extraction.occupation
                if gid_type:
                    ben.government_id_type = GovernmentIdType(gid_type)
                if gnum:
                    ben.government_id_number_masked = _mask_id(gnum)
                # Union of medical conditions (preserve prior history)
                merged = list(
                    dict.fromkeys(
                        [*ben.medical_conditions, *extraction.detected_medical_conditions]
                    )
                )
                ben.medical_conditions = merged
                ben.current_priority = PriorityLevel(urgency.priority)
                ben.urgency = urgency
                ben.source = source
                self.beneficiaries[existing_id] = ben
                return ben

            ben = Beneficiary(
                id=f"ben-{uuid.uuid4().hex[:8]}",
                name=extraction.beneficiary_name or "Unnamed Beneficiary",
                age=extraction.age,
                gender=extraction.gender,
                annual_income=extraction.estimated_household_income,
                state_location=extraction.state_location,
                is_disabled=extraction.is_disabled,
                is_bereaved=extraction.is_bereaved,
                occupation=extraction.occupation,
                government_id_type=GovernmentIdType(gid_type) if gid_type else None,
                government_id_number_masked=_mask_id(gnum),
                medical_conditions=extraction.detected_medical_conditions,
                current_priority=PriorityLevel(urgency.priority),
                urgency=urgency,
                created_at=datetime.now(timezone.utc),
                source=source,
            )
            self.beneficiaries[ben.id] = ben
            if ghash:
                self._gov_id_index[ghash] = ben.id
        return ben

    # --------------------------------------------------------- upload history
    def record_upload(self, entry: UploadHistoryEntry) -> UploadHistoryEntry:
        """Append an audit row. Newest first, capped so a long demo session
        cannot grow memory without bound."""
        with self._lock:
            self.history.insert(0, entry)
            del self.history[500:]
        return entry

    def list_history(self, limit: int = 50) -> list[UploadHistoryEntry]:
        with self._lock:
            return self.history[:limit]

    def seen_document(self, digest: str | None) -> bool:
        """True when this exact file was already ingested (duplicate upload)."""
        if not digest:
            return False
        with self._lock:
            return digest in self._document_hashes

    def remember_document(self, digest: str | None) -> None:
        if not digest:
            return
        with self._lock:
            self._document_hashes.add(digest)

    # ------------------------------------------------------------- documents
    def add_document(
        self, beneficiary_id: str, file_name: str, extracted_text: str,
        parsed: ExtractedDocument,
    ) -> Document:
        doc = Document(
            id=f"doc-{uuid.uuid4().hex[:8]}",
            beneficiary_id=beneficiary_id,
            file_name=file_name,
            file_url=f"local://uploads/{file_name}",
            extracted_text=extracted_text,
            parsed_metadata=parsed,
            created_at=datetime.now(timezone.utc),
        )
        with self._lock:
            self.documents[doc.id] = doc
        return doc

    # ----------------------------------------------------------------- tasks
    def list_tasks(self, beneficiary_id: str | None = None) -> list[Task]:
        with self._lock:
            items = list(self.tasks.values())
            if beneficiary_id:
                items = [t for t in items if t.beneficiary_id == beneficiary_id]
            else:
                # Global task list is scoped to the active mode (via the task's
                # beneficiary), so LIVE mode never surfaces seeded demo tasks.
                visible = {
                    b.id for b in self.beneficiaries.values() if self._is_visible(b)
                }
                items = [t for t in items if t.beneficiary_id in visible]
        items.sort(key=lambda t: (t.due_date or date.max, t.created_at))
        return items

    def add_tasks_from_extraction(
        self, beneficiary_id: str, extraction: ExtractedDocument,
    ) -> list[Task]:
        created: list[Task] = []
        # A follow-up task per detected deadline.
        for dl in extraction.critical_deadlines:
            try:
                due = date.fromisoformat(dl.date)
            except (ValueError, TypeError):
                due = None
            created.append(
                self._make_task(
                    beneficiary_id,
                    title=dl.context or "Follow up on application deadline",
                    description=f"Auto-generated from uploaded document (due {dl.date}).",
                    due_date=due,
                )
            )
        # If a government ID is present but income proof is a common gap, add it.
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
        with self._lock:
            self.tasks[task.id] = task
        return task

    def update_task_status(self, task_id: str, status: TaskStatus) -> Task | None:
        with self._lock:
            task = self.tasks.get(task_id)
            if not task:
                return None
            task.status = status
            self.tasks[task_id] = task
            return task

    # --------------------------------------------------------------- schemes
    def list_schemes(self) -> list[WelfareScheme]:
        with self._lock:
            return list(self.schemes.values())

    def recommend_schemes(
        self, beneficiary: Beneficiary, top_k: int = 6
    ) -> list[SchemeMatch]:
        with self._lock:
            schemes = list(self.schemes.values())
        return recommender.recommend(
            beneficiary, schemes, self._scheme_rules, self._scheme_vectors, top_k
        )

    # ------------------------------------------------------------- dashboard
    def metrics(self) -> DashboardMetrics:
        with self._lock:
            bens = [b for b in self.beneficiaries.values() if self._is_visible(b)]
            visible_ids = {b.id for b in bens}
            tasks = [
                t for t in self.tasks.values() if t.beneficiary_id in visible_ids
            ]
        today = date.today()
        return DashboardMetrics(
            total_beneficiaries=len(bens),
            critical_cases=sum(
                1 for b in bens if b.current_priority == PriorityLevel.CRITICAL
            ),
            high_cases=sum(
                1 for b in bens if b.current_priority == PriorityLevel.HIGH
            ),
            pending_tasks=sum(
                1 for t in tasks if t.status != TaskStatus.COMPLETED
            ),
            overdue_tasks=sum(
                1
                for t in tasks
                if t.status != TaskStatus.COMPLETED
                and t.due_date is not None
                and t.due_date < today
            ),
            schemes_available=len(self.schemes),
        )


def _build_store():
    """Select the persistence backend.

    Supabase-backed (persistent, multi-restart) when configured; otherwise the
    in-memory demo store. Any failure to initialise Supabase falls back to the
    in-memory store so the app always boots — the demo can never be bricked by a
    bad credential.
    """
    import logging

    from app.core.config import settings

    log = logging.getLogger("sahayak.store")
    if settings.supabase_configured:
        try:
            from app.core.supabase_store import SupabaseStore

            s = SupabaseStore()
            log.info("Using SupabaseStore (persistent).")
            return s
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "SupabaseStore init failed (%s) — falling back to in-memory store.",
                exc,
            )
    return DataStore()


store = _build_store()
