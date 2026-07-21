"""Semantic + rule-based welfare recommender — pure, store-agnostic.

Blends deterministic eligibility rules (explainable) with cosine similarity of
1536-dim embeddings (pgvector-style) into a single eligibility `confidence`.
Reused by both the in-memory store and the Supabase-backed store.
"""
from __future__ import annotations

import re

from app.core import ai_engine
from app.models.schemas import Beneficiary, SchemeMatch, WelfareScheme


def beneficiary_context(b: Beneficiary) -> str:
    parts: list[str] = []
    if b.age:
        parts.append(f"{b.age}-year-old")
    if b.gender:
        parts.append(b.gender.lower())
    parts.append("resident")
    if b.state_location:
        parts.append(f"of {b.state_location}")
    if b.annual_income is not None:
        parts.append(f"with an annual household income of {b.annual_income:.0f} INR")
    if b.is_disabled:
        parts.append("with a registered disability")
    if b.medical_conditions:
        parts.append("seeking medical assistance for " + ", ".join(b.medical_conditions))
    else:
        parts.append("seeking welfare and social security support")
    # Life-stage signals give the recommender lexical bridges to the right scheme
    # family (education vs pension) even without a real embedding model.
    if b.age is not None and not b.medical_conditions:
        if 5 <= b.age <= 25:
            parts.append("student seeking education scholarship tuition support")
        elif b.age >= 60:
            parts.append("senior citizen elderly seeking old age pension")
    return " ".join(parts)


# Ceiling applied when a beneficiary merely clears a scheme's screening criteria
# (an income ceiling) without any signal that the scheme is actually FOR them.
# Without this, a scheme whose only rule is `max_income` scores ~1.0 for every
# low-income person — which put a bereavement benefit at the top of every case.
SCREENING_ONLY_CAP = 0.45


def score_rules(b: Beneficiary, rules: dict) -> tuple[float, bool, list[str]]:
    """Return (rule_score 0-1, eligible, reasons).

    Criteria fall into two classes:

      * screening — `max_income`. Answers "is this person NOT excluded?".
        Almost everyone an NGO serves clears it, so on its own it says nothing
        about fit and can never produce a strong match.
      * targeting — age band, disability, gender, medical keywords. Answers
        "is this scheme intended for THIS person?". Only these justify a high
        confidence, and an unknown field never earns targeting credit.
    """
    score = 0.0
    weight = 0.0
    eligible = True
    reasons: list[str] = []
    targeting_matched = False

    # --- screening ---------------------------------------------------------
    if "max_income" in rules:
        weight += 0.30
        if b.annual_income is None:
            score += 0.15
        elif b.annual_income <= rules["max_income"]:
            score += 0.30
            reasons.append(
                f"Income ₹{b.annual_income:,.0f} within limit ₹{rules['max_income']:,.0f}"
            )
        else:
            eligible = False

    # --- targeting: age band ----------------------------------------------
    if "min_age" in rules or "max_age" in rules:
        weight += 0.20
        mn = rules.get("min_age", 0)
        mx = rules.get("max_age", 200)
        if b.age is None:
            score += 0.08  # unknown age: partial credit, but NOT a targeting match
        elif mn <= b.age <= mx:
            score += 0.20
            targeting_matched = True
            reasons.append(f"Age {b.age} within eligible range {mn}–{mx}")
        else:
            eligible = False

    # --- targeting: disability --------------------------------------------
    if rules.get("requires_disability"):
        weight += 0.25
        if b.is_disabled:
            score += 0.25
            targeting_matched = True
            reasons.append("Meets registered disability requirement")
        else:
            eligible = False

    # --- targeting: bereavement (death of the primary breadwinner) ----------
    if rules.get("requires_bereavement"):
        weight += 0.25
        if b.is_bereaved:
            score += 0.25
            targeting_matched = True
            reasons.append("Household has lost its primary breadwinner")
        else:
            eligible = False

    # --- targeting: occupation (livelihood-linked schemes) -----------------
    if "occupations" in rules:
        weight += 0.30
        occ = (b.occupation or "").lower()
        hit = next((o for o in rules["occupations"] if o in occ), None) if occ else None
        if hit:
            score += 0.30
            targeting_matched = True
            reasons.append(f"Occupation '{b.occupation}' matches scheme focus")
        else:
            eligible = False

    # --- targeting: gender -------------------------------------------------
    if "gender" in rules:
        weight += 0.10
        if b.gender and b.gender.lower() == rules["gender"].lower():
            score += 0.10
            targeting_matched = True
            reasons.append(f"Meets {rules['gender']} eligibility")
        else:
            eligible = False

    # --- targeting: medical condition --------------------------------------
    if "medical_keywords" in rules:
        weight += 0.35
        joined = " ".join(b.medical_conditions).lower()
        hit = next(
            (
                k
                for k in rules["medical_keywords"]
                if re.search(rf"\b{re.escape(k)}\b", joined)
            ),
            None,
        )
        if hit:
            score += 0.35
            targeting_matched = True
            reasons.append(f"Medical condition matches scheme focus ('{hit}')")
        elif rules.get("requires_medical_match"):
            # Disease-specific scheme (e.g. a dialysis programme). Recommending it
            # without a matching diagnosis is noise, so exclude it outright.
            eligible = False

    if "keywords" in rules:
        weight += 0.05
        score += 0.03

    if weight == 0:
        return (0.4 if rules.get("is_fallback") else 0.0), True, reasons

    raw = min(1.0, score / weight)
    if not targeting_matched:
        raw = min(raw, SCREENING_ONLY_CAP)

    return raw, eligible, reasons


def recommend(
    beneficiary: Beneficiary,
    schemes: list[WelfareScheme],
    rules_by_id: dict[str, dict],
    vectors_by_id: dict[str, list[float]],
    top_k: int = 6,
) -> list[SchemeMatch]:
    from app.core.config import settings

    context = beneficiary_context(beneficiary)
    ben_vec = ai_engine.embed_text(context)

    # With a real embedding model (LIVE + OpenAI) semantic similarity is meaningful,
    # so it carries real weight. Offline (hashed pseudo-embeddings) it is only a weak
    # lexical signal, so deterministic eligibility RULES must dominate — otherwise
    # noise flips the top recommendation between unrelated documents.
    if settings.use_openai and settings.openai_configured:
        w_rule, w_sem = 0.65, 0.35
    else:
        w_rule, w_sem = 0.85, 0.15

    matches: list[SchemeMatch] = []
    for scheme in schemes:
        rules = rules_by_id.get(scheme.id, {})
        rule_score, eligible, reasons = score_rules(beneficiary, rules)
        vec = vectors_by_id.get(scheme.id) or []
        semantic = ai_engine.cosine_similarity(ben_vec, vec) if vec else 0.0
        is_fallback = bool(rules.get("is_fallback"))

        if not eligible and not is_fallback:
            continue

        confidence = round(w_rule * rule_score + w_sem * semantic, 3)
        if is_fallback:
            confidence = min(confidence, 0.45)
            reasons = reasons or ["General safety-net support when no exact match"]

        matches.append(
            SchemeMatch(
                scheme=scheme,
                confidence=max(0.0, min(1.0, confidence)),
                semantic_similarity=round(semantic, 3),
                rule_score=round(rule_score, 3),
                matched_reasons=reasons[:4],
                is_alternative=is_fallback,
            )
        )

    matches.sort(key=lambda m: (m.is_alternative, -m.confidence))
    # Only schemes with a genuine targeting signal are presented as recommendations.
    # Untargeted ones all land in a narrow ~0.40 band separated by embedding noise,
    # so ranking them invents a preference the evidence does not support (it put a
    # bereavement benefit atop an Aadhaar card). When nothing is targeted we show
    # the safety-net option instead, and the UI flags the missing fields.
    strong = [
        m
        for m in matches
        if not m.is_alternative and m.rule_score > SCREENING_ONLY_CAP
    ]
    if not strong:
        return [m for m in matches if m.is_alternative][:1]
    result = strong[:top_k]
    alt = next((m for m in matches if m.is_alternative), None)
    if alt and len(result) < top_k:
        result.append(alt)
    return result
