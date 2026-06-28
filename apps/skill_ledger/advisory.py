from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Iterable

ADVISORY_CLASSIFICATIONS = {
    "VERIFIED_WITH_EVIDENCE": "Verified - sprint evidence present",
    "VERIFIED_NO_REFERENCE": "Verified - add sprint reference",
    "LEARNING_TARGET": "Learning target - do not claim as verified",
    "STUDYING": "Studying - personal study only",
    "NO_EVIDENCE": "Gap identified - do not claim",
    "PUBLIC_RISK": "Public visibility risk - review before publishing",
    "JD_SIGNAL_UNMATCHED": "Appears in JDs - not yet in ledger",
    "CLAIM_SAFE": "Safe to discuss - evidence confirmed",
}

REQUIRED_SKILL_ADVISORY_SAFETY_WORDING = (
    "Skill Ledger advisory signals are planning aids only.",
    (
        "A skill is claim-ready only when supported by verified project evidence, "
        "tests, screenshots, or prior work experience."
    ),
    "Learning targets must not be presented as verified skills.",
    "JD requirement signals do not prove proficiency.",
    (
        "Review evidence manually before adding any skill to your CV, LinkedIn, "
        "or public profile."
    ),
    "This page does not update your Skill Ledger automatically.",
    (
        "Classifications are generated from your Skill Ledger fields using "
        "deterministic rules, not AI inference."
    ),
    (
        "Public visibility risk means a Skill Ledger entry is set to public but "
        "does not have confirmed evidence. Review before sharing."
    ),
)

ADVISORY_ROW_FIELDS = (
    "skill_name",
    "evidence_level",
    "category",
    "classification",
    "classification_label",
    "claim_ready",
    "public_visibility_risk",
    "advisory_note",
    "action_hint",
    "sprint_reference",
    "project_link",
    "jd_candidate_match",
    "manual_review_required",
)

VERIFIED = "VERIFIED"
LEARNING_TARGET = "LEARNING_TARGET"
STUDYING = "STUDYING"
NO_EVIDENCE = "NO_EVIDENCE"
PUBLIC = "public"


@dataclass(frozen=True)
class SkillAdvisoryRow:
    skill_name: str
    evidence_level: str
    category: str
    classification: str
    classification_label: str
    claim_ready: bool
    public_visibility_risk: bool
    advisory_note: str
    action_hint: str
    sprint_reference: str | None
    project_link: str | None
    jd_candidate_match: bool
    manual_review_required: bool


class SkillAdvisoryValidationError(ValueError):
    """Raised when an advisory value does not satisfy the service contract."""


def _read_mapping_or_attr(value: Any, key: str, default: Any = "") -> Any:
    if isinstance(value, dict):
        return value.get(key, default)
    return getattr(value, key, default)


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _match_key(value: Any) -> str:
    return _clean_text(value).lower()


def _optional_text(value: Any) -> str | None:
    cleaned = _clean_text(value)
    return cleaned or None


def validate_advisory_classification(classification: str) -> str:
    if classification not in ADVISORY_CLASSIFICATIONS:
        raise SkillAdvisoryValidationError("invalid_advisory_classification")
    return classification


def _row_for_unmatched_jd_candidate(term: str) -> SkillAdvisoryRow:
    classification = validate_advisory_classification("JD_SIGNAL_UNMATCHED")
    return SkillAdvisoryRow(
        skill_name=term,
        evidence_level="",
        category="",
        classification=classification,
        classification_label=ADVISORY_CLASSIFICATIONS[classification],
        claim_ready=False,
        public_visibility_risk=False,
        advisory_note=(
            "This term appears in saved JD signals but is not present in the supplied "
            "Skill Ledger entries."
        ),
        action_hint="Review manually before deciding whether to add evidence.",
        sprint_reference=None,
        project_link=None,
        jd_candidate_match=True,
        manual_review_required=True,
    )


def build_skill_advisory_row(
    entry: Any,
    *,
    jd_candidate_terms: tuple[str, ...] = (),
) -> SkillAdvisoryRow:
    skill_name = _clean_text(_read_mapping_or_attr(entry, "skill_name"))
    evidence_level = _clean_text(_read_mapping_or_attr(entry, "evidence_level"))
    category = _clean_text(_read_mapping_or_attr(entry, "category"))
    sprint_reference = _optional_text(_read_mapping_or_attr(entry, "sprint_reference"))
    project_link = _optional_text(_read_mapping_or_attr(entry, "project_link"))
    visibility = _clean_text(_read_mapping_or_attr(entry, "visibility")).lower()
    jd_candidate_match = _match_key(skill_name) in {_match_key(term) for term in jd_candidate_terms}

    public_visibility_risk = visibility == PUBLIC and evidence_level != VERIFIED
    claim_ready = False
    manual_review_required = True

    if public_visibility_risk:
        classification = "PUBLIC_RISK"
        advisory_note = "This public entry does not have confirmed evidence."
        action_hint = "Set visibility to private or add evidence before sharing."
    elif evidence_level == VERIFIED and sprint_reference and project_link:
        classification = "CLAIM_SAFE"
        claim_ready = True
        manual_review_required = False
        advisory_note = "Verified project evidence and sprint reference are present."
        action_hint = "Use the linked evidence when discussing this skill."
    elif evidence_level == VERIFIED and sprint_reference:
        classification = "VERIFIED_WITH_EVIDENCE"
        advisory_note = (
            "Sprint evidence is present, but project evidence should be linked manually."
        )
        action_hint = "Add a project link before using this skill in public materials."
    elif evidence_level == VERIFIED:
        classification = "VERIFIED_NO_REFERENCE"
        advisory_note = "Verified status needs a sprint reference before public use."
        action_hint = "Add the sprint reference and review supporting evidence manually."
    elif evidence_level == LEARNING_TARGET:
        classification = "LEARNING_TARGET"
        advisory_note = "This is a learning target and must not be presented as verified."
        action_hint = "Keep this as a learning plan item until evidence is added."
    elif evidence_level == STUDYING:
        classification = "STUDYING"
        advisory_note = "This is personal study only and needs evidence before public use."
        action_hint = "Continue study and add project evidence when available."
    else:
        classification = "NO_EVIDENCE"
        advisory_note = "No supporting evidence is recorded for this skill."
        action_hint = "Treat this as a gap until evidence is added and reviewed."

    classification = validate_advisory_classification(classification)
    return SkillAdvisoryRow(
        skill_name=skill_name,
        evidence_level=evidence_level,
        category=category,
        classification=classification,
        classification_label=ADVISORY_CLASSIFICATIONS[classification],
        claim_ready=claim_ready,
        public_visibility_risk=public_visibility_risk,
        advisory_note=advisory_note,
        action_hint=action_hint,
        sprint_reference=sprint_reference,
        project_link=project_link,
        jd_candidate_match=jd_candidate_match,
        manual_review_required=manual_review_required,
    )


def build_skill_advisory_rows(
    entries: Iterable[Any],
    *,
    jd_candidate_terms: Iterable[str] = (),
) -> tuple[SkillAdvisoryRow, ...]:
    cleaned_jd_terms = tuple(
        dict.fromkeys(
            term for term in (_clean_text(value) for value in jd_candidate_terms) if term
        ),
    )
    rows = tuple(
        build_skill_advisory_row(entry, jd_candidate_terms=cleaned_jd_terms)
        for entry in entries
    )
    ledger_keys = {_match_key(row.skill_name) for row in rows}
    unmatched_rows = tuple(
        _row_for_unmatched_jd_candidate(term)
        for term in cleaned_jd_terms
        if _match_key(term) not in ledger_keys
    )
    return (*rows, *unmatched_rows)


def validate_skill_advisory_row_schema(
    row: SkillAdvisoryRow | dict[str, Any],
) -> SkillAdvisoryRow:
    if isinstance(row, dict):
        keys = set(row)
        expected = set(ADVISORY_ROW_FIELDS)
        if keys != expected:
            if keys - expected:
                raise SkillAdvisoryValidationError("extra_schema_keys")
            raise SkillAdvisoryValidationError("missing_required_fields")
        row = SkillAdvisoryRow(**row)

    field_names = tuple(field.name for field in fields(SkillAdvisoryRow))
    if field_names != ADVISORY_ROW_FIELDS:
        raise SkillAdvisoryValidationError("invalid_schema_fields")
    validate_advisory_classification(row.classification)
    if row.classification_label != ADVISORY_CLASSIFICATIONS[row.classification]:
        raise SkillAdvisoryValidationError("invalid_classification_label")
    return row


def advisory_row_to_template_dict(row: SkillAdvisoryRow) -> dict[str, Any]:
    return asdict(validate_skill_advisory_row_schema(row))
