"""Deterministic Skill Ledger to JD gap classifier (Sprint 110B Phase 1).

Pure domain logic. No ORM, forms, views, providers or network I/O.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

from apps.skill_gaps.services import SKILL_ALIAS_MAP, normalise_skill_match_key


class RequirementClassification(str, Enum):
    VERIFIED_MATCH = "VERIFIED_MATCH"
    LEARNING_TARGET_MATCH = "LEARNING_TARGET_MATCH"
    STUDYING_MATCH = "STUDYING_MATCH"
    NO_EVIDENCE_GAP = "NO_EVIDENCE_GAP"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"


class MatchBasis(str, Enum):
    EXACT_NAME = "exact_name"
    CURATED_ALIAS = "curated_alias"
    NO_MATCH = "no_match"
    NO_EVIDENCE = "no_evidence"
    DUPLICATE_EVIDENCE = "duplicate_evidence"
    CONFLICTING_EVIDENCE = "conflicting_evidence"
    CLAIM_SCOPE_REVIEW = "claim_scope_review"
    COMPOUND_REQUIREMENT_REVIEW = "compound_requirement_review"


YEARS_OF_EXPERIENCE_WORDING = "YEARS_OF_EXPERIENCE_WORDING"
SENIORITY_WORDING = "SENIORITY_WORDING"
EXPERT_PROFICIENCY_WORDING = "EXPERT_PROFICIENCY_WORDING"
PRODUCTION_EXPERIENCE_WORDING = "PRODUCTION_EXPERIENCE_WORDING"
ENTERPRISE_SCALE_WORDING = "ENTERPRISE_SCALE_WORDING"
COMMERCIAL_DEPLOYMENT_WORDING = "COMMERCIAL_DEPLOYMENT_WORDING"
LEADERSHIP_OWNERSHIP_WORDING = "LEADERSHIP_OWNERSHIP_WORDING"
ADMINISTRATION_RESPONSIBILITY_WORDING = "ADMINISTRATION_RESPONSIBILITY_WORDING"
SECURITY_RESPONSIBILITY_WORDING = "SECURITY_RESPONSIBILITY_WORDING"
COMPLIANCE_REGULATORY_WORDING = "COMPLIANCE_REGULATORY_WORDING"
DUPLICATE_SKILL_ENTRIES = "DUPLICATE_SKILL_ENTRIES"
CONFLICTING_EVIDENCE_LEVELS = "CONFLICTING_EVIDENCE_LEVELS"
COMPOUND_REQUIREMENT = "COMPOUND_REQUIREMENT"

_BULLET_PREFIX_RE = re.compile(
    r"^(?:[-*\u2022]|\d+[.)])\s+",
)

_YEARS_RE = re.compile(
    r"\b(?:\d{1,2}\s*\+?|one|two|three|four|five|six|seven|eight|nine|ten)"
    r"\s*(?:years?|yrs?)\b",
    re.IGNORECASE,
)

_SENIORITY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "senior",
        "principal",
        "director",
        "chief",
        "head of",
        "vice president",
        "vp",
        "staff engineer",
        "staff developer",
        "staff analyst",
        "staff scientist",
        "lead engineer",
        "lead developer",
        "lead analyst",
        "lead scientist",
        "lead architect",
        "team lead",
    )
)

_EXPERT_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in ("expert", "advanced", "mastery", "highly proficient")
)

_PRODUCTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "production",
        "production-grade",
        "production grade",
        "production-level",
        "production level",
        "production-ready",
        "production ready",
    )
)

_ENTERPRISE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "enterprise-scale",
        "enterprise scale",
        "large-scale",
        "large scale",
        "at scale",
    )
)

_COMMERCIAL_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "commercial deployment",
        "commercially deployed",
        "shipped to production",
        "live production",
    )
)

_LEADERSHIP_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "leadership",
        "team leadership",
        "led a team",
        "managed a team",
        "owned the",
        "ownership of",
    )
)

_ADMINISTRATION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "administration",
        "administrator",
        "sysadmin",
        "administering",
    )
)

_SECURITY_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "security responsibility",
        "security responsibilities",
        "security ownership",
        "security clearance",
    )
)

_COMPLIANCE_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(rf"\b{re.escape(signal)}\b", re.IGNORECASE)
    for signal in (
        "compliance",
        "regulatory",
        "audit responsibility",
        "audit responsibilities",
    )
)

_CLAIM_SCOPE_CHECKS: tuple[tuple[str, tuple[re.Pattern[str], ...]], ...] = (
    (SENIORITY_WORDING, _SENIORITY_PATTERNS),
    (EXPERT_PROFICIENCY_WORDING, _EXPERT_PATTERNS),
    (PRODUCTION_EXPERIENCE_WORDING, _PRODUCTION_PATTERNS),
    (ENTERPRISE_SCALE_WORDING, _ENTERPRISE_PATTERNS),
    (COMMERCIAL_DEPLOYMENT_WORDING, _COMMERCIAL_PATTERNS),
    (LEADERSHIP_OWNERSHIP_WORDING, _LEADERSHIP_PATTERNS),
    (ADMINISTRATION_RESPONSIBILITY_WORDING, _ADMINISTRATION_PATTERNS),
    (SECURITY_RESPONSIBILITY_WORDING, _SECURITY_PATTERNS),
    (COMPLIANCE_REGULATORY_WORDING, _COMPLIANCE_PATTERNS),
)

_SEPARATOR_RE = re.compile(r"\s*(?:,|/|&|\band\b)\s*", re.IGNORECASE)
_HAS_SEPARATOR_RE = re.compile(r"(?:,|/|&|\band\b)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class SkillLedgerEvidence:
    entry_id: int
    skill_name: str
    evidence_level: str


@dataclass(frozen=True, slots=True)
class NormalisedRequirement:
    requirement_index: int
    original_text: str
    normalised_text: str
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RequirementMatchResult:
    requirement_index: int
    original_text: str
    normalised_text: str
    classification: RequirementClassification
    match_basis: MatchBasis
    matched_skill_name: str | None
    matched_evidence_level: str | None
    matched_skill_entry_id: int | None
    reason_codes: tuple[str, ...]


def _strip_approved_prefix(value: str) -> str:
    return _BULLET_PREFIX_RE.sub("", value, count=1)


def _pre_alias_forms(value: str) -> tuple[str, str]:
    """Return (cleaned, punctuation_canonical) before alias lookup."""
    raw_value = "" if value is None else str(value)
    cleaned = " ".join(raw_value.strip().lower().split())
    if not cleaned:
        return "", ""
    punctuation_normalised = re.sub(r"[^\w\s]+", " ", cleaned)
    punctuation_normalised = punctuation_normalised.replace("_", " ")
    canonical = " ".join(punctuation_normalised.split())
    return cleaned, canonical


def _used_curated_alias(value: str) -> bool:
    cleaned, canonical = _pre_alias_forms(value)
    if not cleaned:
        return False
    if cleaned in SKILL_ALIAS_MAP:
        return True
    return canonical in SKILL_ALIAS_MAP


def _claim_scope_reason_codes(comparison_source: str) -> tuple[str, ...]:
    spaced = " ".join(comparison_source.strip().lower().split())
    if not spaced:
        return ()
    _, punct = _pre_alias_forms(comparison_source)
    texts = (spaced, punct) if punct and punct != spaced else (spaced,)

    codes: list[str] = []
    if any(_YEARS_RE.search(text) for text in texts):
        codes.append(YEARS_OF_EXPERIENCE_WORDING)
    for code, patterns in _CLAIM_SCOPE_CHECKS:
        if any(pattern.search(text) for text in texts for pattern in patterns):
            codes.append(code)
    return tuple(codes)


def normalise_requirement(
    requirement_index: int,
    raw_text: str,
) -> NormalisedRequirement:
    original_text = "" if raw_text is None else str(raw_text).strip()
    comparison_source = _strip_approved_prefix(original_text)
    comparison_source = unicodedata.normalize("NFKC", comparison_source)
    normalised_text = normalise_skill_match_key(comparison_source)
    reason_codes = _claim_scope_reason_codes(comparison_source)
    return NormalisedRequirement(
        requirement_index=requirement_index,
        original_text=original_text,
        normalised_text=normalised_text,
        reason_codes=reason_codes,
    )


def _evidence_key(entry: SkillLedgerEvidence) -> str:
    return normalise_skill_match_key(entry.skill_name)


def _build_evidence_index(
    evidence: tuple[SkillLedgerEvidence, ...],
) -> dict[str, tuple[SkillLedgerEvidence, ...]]:
    buckets: dict[str, list[SkillLedgerEvidence]] = {}
    for entry in evidence:
        key = _evidence_key(entry)
        if not key:
            continue
        buckets.setdefault(key, []).append(entry)
    return {key: tuple(rows) for key, rows in buckets.items()}


def _is_compound_requirement(
    comparison_source: str,
    evidence_keys: frozenset[str],
) -> bool:
    if not _HAS_SEPARATOR_RE.search(comparison_source):
        return False
    segments = [segment for segment in _SEPARATOR_RE.split(comparison_source) if segment]
    if len(segments) < 2:
        return False
    recognised: list[str] = []
    seen: set[str] = set()
    for segment in segments:
        key = normalise_skill_match_key(segment)
        if not key:
            continue
        if key in evidence_keys and key not in seen:
            seen.add(key)
            recognised.append(key)
    return len(recognised) >= 2


def _single_match_result(
    requirement: NormalisedRequirement,
    entry: SkillLedgerEvidence,
    comparison_source: str,
) -> RequirementMatchResult:
    level = entry.evidence_level
    used_alias = _used_curated_alias(comparison_source)
    basis = MatchBasis.CURATED_ALIAS if used_alias else MatchBasis.EXACT_NAME

    if level == "VERIFIED":
        classification = RequirementClassification.VERIFIED_MATCH
        match_basis = basis
    elif level == "LEARNING_TARGET":
        classification = RequirementClassification.LEARNING_TARGET_MATCH
        match_basis = basis
    elif level == "STUDYING":
        classification = RequirementClassification.STUDYING_MATCH
        match_basis = basis
    elif level == "NO_EVIDENCE":
        classification = RequirementClassification.NO_EVIDENCE_GAP
        match_basis = MatchBasis.NO_EVIDENCE
    else:
        # Unrecognised evidence level is treated as a no-match gap.
        return RequirementMatchResult(
            requirement_index=requirement.requirement_index,
            original_text=requirement.original_text,
            normalised_text=requirement.normalised_text,
            classification=RequirementClassification.NO_EVIDENCE_GAP,
            match_basis=MatchBasis.NO_MATCH,
            matched_skill_name=None,
            matched_evidence_level=None,
            matched_skill_entry_id=None,
            reason_codes=requirement.reason_codes,
        )

    return RequirementMatchResult(
        requirement_index=requirement.requirement_index,
        original_text=requirement.original_text,
        normalised_text=requirement.normalised_text,
        classification=classification,
        match_basis=match_basis,
        matched_skill_name=entry.skill_name,
        matched_evidence_level=level,
        matched_skill_entry_id=entry.entry_id,
        reason_codes=requirement.reason_codes,
    )


def classify_requirement(
    requirement: NormalisedRequirement,
    evidence: tuple[SkillLedgerEvidence, ...],
) -> RequirementMatchResult:
    comparison_source = _strip_approved_prefix(requirement.original_text)
    comparison_source = unicodedata.normalize("NFKC", comparison_source)
    evidence_index = _build_evidence_index(evidence)
    evidence_keys = frozenset(evidence_index)

    # 1. Compound requirement
    if _is_compound_requirement(comparison_source, evidence_keys):
        return RequirementMatchResult(
            requirement_index=requirement.requirement_index,
            original_text=requirement.original_text,
            normalised_text=requirement.normalised_text,
            classification=RequirementClassification.REVIEW_REQUIRED,
            match_basis=MatchBasis.COMPOUND_REQUIREMENT_REVIEW,
            matched_skill_name=None,
            matched_evidence_level=None,
            matched_skill_entry_id=None,
            reason_codes=requirement.reason_codes + (COMPOUND_REQUIREMENT,),
        )

    # 2. Claim-scope reason present
    if requirement.reason_codes:
        return RequirementMatchResult(
            requirement_index=requirement.requirement_index,
            original_text=requirement.original_text,
            normalised_text=requirement.normalised_text,
            classification=RequirementClassification.REVIEW_REQUIRED,
            match_basis=MatchBasis.CLAIM_SCOPE_REVIEW,
            matched_skill_name=None,
            matched_evidence_level=None,
            matched_skill_entry_id=None,
            reason_codes=requirement.reason_codes,
        )

    match_key = requirement.normalised_text
    matches = evidence_index.get(match_key, ())

    # 3. No matching evidence row
    if not matches:
        return RequirementMatchResult(
            requirement_index=requirement.requirement_index,
            original_text=requirement.original_text,
            normalised_text=requirement.normalised_text,
            classification=RequirementClassification.NO_EVIDENCE_GAP,
            match_basis=MatchBasis.NO_MATCH,
            matched_skill_name=None,
            matched_evidence_level=None,
            matched_skill_entry_id=None,
            reason_codes=requirement.reason_codes,
        )

    if len(matches) > 1:
        levels = {entry.evidence_level for entry in matches}
        # 4. Conflicting evidence levels
        if len(levels) > 1:
            return RequirementMatchResult(
                requirement_index=requirement.requirement_index,
                original_text=requirement.original_text,
                normalised_text=requirement.normalised_text,
                classification=RequirementClassification.REVIEW_REQUIRED,
                match_basis=MatchBasis.CONFLICTING_EVIDENCE,
                matched_skill_name=None,
                matched_evidence_level=None,
                matched_skill_entry_id=None,
                reason_codes=requirement.reason_codes
                + (CONFLICTING_EVIDENCE_LEVELS,),
            )
        # 5. Same-level duplicates
        return RequirementMatchResult(
            requirement_index=requirement.requirement_index,
            original_text=requirement.original_text,
            normalised_text=requirement.normalised_text,
            classification=RequirementClassification.REVIEW_REQUIRED,
            match_basis=MatchBasis.DUPLICATE_EVIDENCE,
            matched_skill_name=None,
            matched_evidence_level=None,
            matched_skill_entry_id=None,
            reason_codes=requirement.reason_codes + (DUPLICATE_SKILL_ENTRIES,),
        )

    # 6-9. Single matching row
    return _single_match_result(requirement, matches[0], comparison_source)


def classify_requirements(
    requirements: tuple[NormalisedRequirement, ...],
    evidence: tuple[SkillLedgerEvidence, ...],
) -> tuple[RequirementMatchResult, ...]:
    return tuple(
        classify_requirement(requirement, evidence) for requirement in requirements
    )
