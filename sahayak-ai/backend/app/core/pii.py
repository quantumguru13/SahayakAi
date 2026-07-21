"""PII helpers shared by the in-memory and Supabase stores.

We deliberately never persist a raw government ID number: only a masked display
value and a salted-free SHA-256 hash (used purely for dedup) are stored.
"""
from __future__ import annotations

import hashlib
import re


def mask_id(id_number: str | None) -> str | None:
    if not id_number:
        return None
    digits = id_number.replace(" ", "")
    if len(digits) <= 4:
        return "••••"
    return "•••• •••• " + digits[-4:]


def gov_hash(id_number: str | None) -> str | None:
    """Stable hash of a normalized government ID for dedup — avoids keeping the
    raw PII value anywhere."""
    if not id_number:
        return None
    normalized = re.sub(r"\s+", "", id_number).upper()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
