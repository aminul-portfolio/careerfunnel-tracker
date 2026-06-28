from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from typing import Any, Iterable

from .advisory import (
    SkillAdvisoryRow,
    SkillAdvisoryValidationError,
    validate_skill_advisory_row_schema,
)

SPRINT_87_PROVIDER_MODE_MOCKED = "mocked"

REQUIRED_EXPLANATION_SAFETY_WARNING = (
    "This explanation is advisory only and does not verify proficiency, certify skills, "
    "or predict employer outcomes."
)

FORBIDDEN_EXPLANATION_PHRASES = (
    "employer confirmed",
    "you are qualified",
    "job ready",
    "employer ready",
    "this proves proficiency",
    "ai verified",
    "automatically verified",
    "skill confirmed",
    "ready to apply",
    "you meet the requirements",
    "this jd signal verifies",
    "proficiency confirmed",
)


@dataclass(frozen=True)
class SkillAdvisoryExplanation:
    skill_name: str
    classification: str
    evidence_basis: str
    jd_signal_context: str
    claim_safety_warning: str
    manual_next_action: str
    source_limitations: str
    confidence_boundary: str
    provider_mode: str


def validate_explanation(explanation: Any) -> SkillAdvisoryExplanation:
    if not isinstance(explanation, SkillAdvisoryExplanation):
        raise SkillAdvisoryValidationError("invalid_explanation_type")

    values = asdict(explanation)
    for field_name, value in values.items():
        if value is None:
            raise SkillAdvisoryValidationError(f"{field_name}_cannot_be_none")
        if not isinstance(value, str):
            raise SkillAdvisoryValidationError(f"{field_name}_must_be_string")

    if not explanation.claim_safety_warning:
        raise SkillAdvisoryValidationError("claim_safety_warning_required")
    if explanation.provider_mode != SPRINT_87_PROVIDER_MODE_MOCKED:
        raise SkillAdvisoryValidationError("invalid_provider_mode")
    if REQUIRED_EXPLANATION_SAFETY_WARNING not in explanation.claim_safety_warning:
        raise SkillAdvisoryValidationError("missing_required_safety_warning")

    combined_text = " ".join(values.values()).lower()
    for phrase in FORBIDDEN_EXPLANATION_PHRASES:
        if phrase in combined_text:
            raise SkillAdvisoryValidationError("forbidden_explanation_phrase")

    return explanation


def build_skill_advisory_explanation(
    row: SkillAdvisoryRow | dict[str, Any],
) -> SkillAdvisoryExplanation:
    validated_row = validate_skill_advisory_row_schema(row)
    jd_context = (
        "Saved JD signal context is present for this advisory row."
        if validated_row.jd_candidate_match
        else ""
    )
    evidence_parts = (
        f"Classification: {validated_row.classification_label}.",
        f"Evidence level: {validated_row.evidence_level or 'not recorded'}.",
        f"Advisory basis: {validated_row.advisory_note}",
    )
    source_limitations = (
        "This uses only the supplied Skill Advisory row fields: classification, "
        "evidence level, advisory note, action hint, and JD signal flag."
    )
    confidence_boundary = (
        "Deterministic Sprint 87 contract output only; manual review remains required."
        if validated_row.manual_review_required
        else (
            "Deterministic Sprint 87 contract output only; supporting evidence still "
            "needs manual review before reuse."
        )
    )

    explanation = SkillAdvisoryExplanation(
        skill_name=validated_row.skill_name,
        classification=validated_row.classification,
        evidence_basis=" ".join(evidence_parts),
        jd_signal_context=jd_context,
        claim_safety_warning=REQUIRED_EXPLANATION_SAFETY_WARNING,
        manual_next_action=validated_row.action_hint,
        source_limitations=source_limitations,
        confidence_boundary=confidence_boundary,
        provider_mode=SPRINT_87_PROVIDER_MODE_MOCKED,
    )
    return validate_explanation(explanation)


def build_skill_advisory_explanations(
    rows: Iterable[SkillAdvisoryRow | dict[str, Any]],
) -> tuple[SkillAdvisoryExplanation, ...]:
    return tuple(build_skill_advisory_explanation(row) for row in rows)


def explanation_to_dict(explanation: SkillAdvisoryExplanation) -> dict[str, str]:
    return {
        field.name: getattr(validate_explanation(explanation), field.name)
        for field in fields(SkillAdvisoryExplanation)
    }
