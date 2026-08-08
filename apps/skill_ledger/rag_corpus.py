"""Ownership-scoped SkillEntry RAG corpus helpers (Sprint 119 Phase 1).

Corpus construction always starts from SkillEntry.objects.for_user(user).
Canonical retrieval text uses only the approved field set.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .models import SkillEntry

APPROVED_CANONICAL_FIELDS: tuple[str, ...] = (
    "skill_name",
    "category",
    "evidence_level",
    "sprint_reference",
)

EXCLUDED_CANONICAL_FIELDS: frozenset[str] = frozenset(
    {
        "notes",
        "project_link",
        "visibility",
        "user",
        "user_id",
        "date_added",
        "last_updated",
        "id",
        "pk",
    }
)


def canonical_json_bytes(value: Any) -> bytes:
    """Deterministic UTF-8 JSON bytes (repository canonical policy)."""
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_hex(value: Any) -> str:
    """Lowercase SHA-256 hex digest of canonical JSON bytes."""
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def build_canonical_source_representation(entry: SkillEntry) -> dict[str, str]:
    """Return the approved-field-only canonical representation for one entry."""
    return {
        "category": entry.category,
        "evidence_level": entry.evidence_level,
        "skill_name": entry.skill_name,
        "sprint_reference": entry.sprint_reference,
    }


def content_sha256_for_entry(entry: SkillEntry) -> str:
    """SHA-256 identity of the approved canonical source representation."""
    return sha256_hex(build_canonical_source_representation(entry))


@dataclass(frozen=True)
class SkillEvidenceCorpusItem:
    skill_entry_id: int
    skill_name: str
    category: str
    evidence_level: str
    sprint_reference: str
    content_sha256: str
    canonical_representation: dict[str, str]


def build_skill_evidence_corpus(user) -> tuple[SkillEvidenceCorpusItem, ...]:
    """Build an ownership-scoped corpus from SkillEntry.objects.for_user(user).

    Never constructs a global SkillEntry set filtered later by user.
    """
    owned_entries = SkillEntry.objects.for_user(user).order_by("pk")
    items: list[SkillEvidenceCorpusItem] = []
    for entry in owned_entries:
        canonical = build_canonical_source_representation(entry)
        items.append(
            SkillEvidenceCorpusItem(
                skill_entry_id=entry.pk,
                skill_name=entry.skill_name,
                category=entry.category,
                evidence_level=entry.evidence_level,
                sprint_reference=entry.sprint_reference,
                content_sha256=sha256_hex(canonical),
                canonical_representation=canonical,
            )
        )
    return tuple(items)
