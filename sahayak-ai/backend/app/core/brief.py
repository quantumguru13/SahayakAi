"""AI Daily Brief + Impact Report generation.

Deterministic by default (works flawlessly in demo mode). When OpenAI is
configured the brief headline is optionally sharpened by gpt-4o, but the
structured actions/metrics always come from the deterministic engine so the
5-minute demo never renders an empty or broken panel.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.config import settings
from app.core.store import store
from app.models.schemas import (
    BriefAction,
    DailyBrief,
    ImpactReport,
    PriorityLevel,
    TaskStatus,
)


def build_daily_brief() -> DailyBrief:
    metrics = store.metrics()
    beneficiaries = store.list_beneficiaries()
    tasks = store.list_tasks()
    today = date.today()

    # Top actions: overdue tasks first, then tasks for critical/high beneficiaries.
    ben_by_id = {b.id: b for b in beneficiaries}
    scored: list[tuple[int, BriefAction]] = []
    for t in tasks:
        if t.status == TaskStatus.COMPLETED:
            continue
        ben = ben_by_id.get(t.beneficiary_id)
        prio = ben.current_priority if ben else PriorityLevel.MEDIUM
        overdue = t.due_date is not None and t.due_date < today
        days_left = (t.due_date - today).days if t.due_date else 999

        rank = 0
        reason_bits = []
        if overdue:
            rank -= 100
            reason_bits.append(f"OVERDUE by {abs(days_left)}d")
        elif days_left <= 3:
            rank -= 60
            reason_bits.append(f"due in {days_left}d")
        elif days_left <= 7:
            rank -= 30
            reason_bits.append(f"due in {days_left}d")
        if prio == PriorityLevel.CRITICAL:
            rank -= 50
            reason_bits.append("CRITICAL case")
        elif prio == PriorityLevel.HIGH:
            rank -= 20
            reason_bits.append("high-priority case")

        reason = ", ".join(reason_bits) or "pending follow-up"
        scored.append(
            (
                rank,
                BriefAction(
                    beneficiary_id=ben.id if ben else None,
                    beneficiary_name=ben.name if ben else None,
                    action=t.title,
                    reason=reason,
                    priority=prio,
                ),
            )
        )

    scored.sort(key=lambda x: x[0])
    top_actions = [a for _, a in scored[:3]]
    system_healthy = metrics.overdue_tasks == 0 and metrics.critical_cases == 0

    if system_healthy:
        headline = "All clear — no overdue tasks or critical cases today."
        summary = (
            "### ✅ System Healthy\n\n"
            "You have no overdue tasks and no critical cases requiring immediate "
            "attention. Great work keeping every lifeline on track."
        )
    else:
        headline = (
            f"{metrics.critical_cases} critical case(s) and "
            f"{metrics.overdue_tasks} overdue task(s) need attention today."
        )
        lines = [
            "### ☀️ Good morning — here's your field brief",
            "",
            f"You are actively managing **{metrics.total_beneficiaries} beneficiaries**. "
            f"**{metrics.critical_cases} critical** and **{metrics.high_cases} high-priority** "
            f"cases are on the board, with **{metrics.pending_tasks} open tasks** "
            f"(**{metrics.overdue_tasks} overdue**).",
            "",
            "**Top 3 priorities right now:**",
        ]
        for i, a in enumerate(top_actions, 1):
            who = f" — _{a.beneficiary_name}_" if a.beneficiary_name else ""
            lines.append(f"{i}. **{a.action}**{who} ({a.reason})")
        lines += [
            "",
            "> Handle overdue and critical items first — these are the lifelines most "
            "at risk of slipping through the cracks.",
        ]
        summary = "\n".join(lines)

    # Deterministic headline unless OpenAI is explicitly enabled — the brief must
    # render instantly and offline during the demo.
    if settings.use_openai and settings.openai_configured:
        headline = _maybe_llm_headline(headline, metrics, top_actions) or headline

    return DailyBrief(
        generated_at=datetime.now(timezone.utc),
        headline=headline,
        summary_markdown=summary,
        top_actions=top_actions,
        metrics=metrics,
        system_healthy=system_healthy,
    )


def _maybe_llm_headline(fallback: str, metrics, actions) -> str | None:
    try:
        from app.core.ai_engine import _client

        action_txt = "; ".join(f"{a.action} ({a.reason})" for a in actions)
        resp = _client().chat.completions.create(
            model=settings.openai_chat_model,
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": "You write one-sentence motivating daily briefs for an "
                    "NGO field worker. Be concrete and under 25 words.",
                },
                {
                    "role": "user",
                    "content": f"Critical cases: {metrics.critical_cases}, overdue tasks: "
                    f"{metrics.overdue_tasks}. Top actions: {action_txt}",
                },
            ],
        )
        return (resp.choices[0].message.content or "").strip() or None
    except Exception as exc:
        from app.core.ai_engine import _handle_openai_error
        _handle_openai_error(exc)
        return None


def build_impact_report() -> ImpactReport:
    metrics = store.metrics()
    beneficiaries = store.list_beneficiaries()
    tasks = store.list_tasks()
    completed = [t for t in tasks if t.status == TaskStatus.COMPLETED]
    in_progress = [t for t in tasks if t.status == TaskStatus.IN_PROGRESS]

    by_state: dict[str, int] = {}
    for b in beneficiaries:
        if b.state_location:
            by_state[b.state_location] = by_state.get(b.state_location, 0) + 1

    total_tasks = len(tasks) or 1
    resolution_rate = round(100 * len(completed) / total_tasks)

    stats = {
        "total_beneficiaries": metrics.total_beneficiaries,
        "critical_cases": metrics.critical_cases,
        "high_cases": metrics.high_cases,
        "tasks_total": len(tasks),
        "tasks_completed": len(completed),
        "tasks_in_progress": len(in_progress),
        "resolution_rate_pct": resolution_rate,
        "schemes_available": metrics.schemes_available,
        "coverage_by_state": by_state,
    }

    now = datetime.now(timezone.utc)
    if metrics.total_beneficiaries == 0:
        md = (
            "# Sahayak AI — Impact Summary Report\n\n"
            "_No case data logged yet. This is an empty structured framework ready to "
            "populate as cases are onboarded._\n"
        )
    else:
        state_lines = "\n".join(
            f"- **{s}**: {c} beneficiaries" for s, c in sorted(by_state.items())
        ) or "- (location data pending)"
        md = f"""# Sahayak AI — Impact Summary Report

**Generated:** {now.strftime('%d %B %Y, %H:%M UTC')}
**Reporting period:** Cumulative to date

## Executive Summary
Our field team is actively supporting **{metrics.total_beneficiaries} vulnerable
beneficiaries** across **{len(by_state)} state(s)**. Through AI-assisted intake and
proactive prioritization we are tracking **{metrics.critical_cases} critical** and
**{metrics.high_cases} high-priority** cases, ensuring the most urgent lifelines are
never missed.

## Operational Metrics
| Metric | Value |
| --- | --- |
| Beneficiaries onboarded | {metrics.total_beneficiaries} |
| Critical cases | {metrics.critical_cases} |
| High-priority cases | {metrics.high_cases} |
| Total follow-up tasks | {len(tasks)} |
| Tasks completed | {len(completed)} |
| Task resolution rate | {resolution_rate}% |
| Welfare schemes matched against | {metrics.schemes_available} |

## Regional Coverage
{state_lines}

## Outcome Narrative
By automating document intake and welfare-scheme matching, Sahayak AI has reduced
administrative overhead and surfaced time-critical deadlines that would otherwise
be lost in fragmented WhatsApp threads and paper forms. Every case above represents
a family kept connected to the welfare infrastructure they are entitled to.

_This report was generated automatically for donor and CSR reporting._
"""

    return ImpactReport(
        generated_at=now,
        title="Sahayak AI — Impact Summary Report",
        period="Cumulative to date",
        markdown=md,
        stats=stats,
    )
