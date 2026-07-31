"""Deterministic evidence alignment aggregation (Sprint 111B Phase 1).

Pure domain aggregation over Sprint 110B RequirementMatchResult tuples.
No ORM, forms, views, providers, network I/O or filesystem writes.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from apps.skill_gaps.deterministic_gap_classifier import (
    MatchBasis,
    RequirementClassification,
    RequirementMatchResult,
)

RULE_VERSION = "evidence_alignment_v1"

_VALID_PAIRS: frozenset[tuple[RequirementClassification, MatchBasis]] = frozenset(
    {
        (RequirementClassification.VERIFIED_MATCH, MatchBasis.EXACT_NAME),
        (RequirementClassification.VERIFIED_MATCH, MatchBasis.CURATED_ALIAS),
        (RequirementClassification.LEARNING_TARGET_MATCH, MatchBasis.EXACT_NAME),
        (RequirementClassification.LEARNING_TARGET_MATCH, MatchBasis.CURATED_ALIAS),
        (RequirementClassification.STUDYING_MATCH, MatchBasis.EXACT_NAME),
        (RequirementClassification.STUDYING_MATCH, MatchBasis.CURATED_ALIAS),
        (RequirementClassification.NO_EVIDENCE_GAP, MatchBasis.NO_MATCH),
        (RequirementClassification.NO_EVIDENCE_GAP, MatchBasis.NO_EVIDENCE),
        (RequirementClassification.REVIEW_REQUIRED, MatchBasis.DUPLICATE_EVIDENCE),
        (RequirementClassification.REVIEW_REQUIRED, MatchBasis.CONFLICTING_EVIDENCE),
        (RequirementClassification.REVIEW_REQUIRED, MatchBasis.CLAIM_SCOPE_REVIEW),
        (RequirementClassification.REVIEW_REQUIRED, MatchBasis.COMPOUND_REQUIREMENT_REVIEW),
    }
)


class EvidenceAlignmentOutcome(str, Enum):
    NO_ACCEPTED_REQUIREMENTS = "NO_ACCEPTED_REQUIREMENTS"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"
    ALL_REQUIREMENTS_VERIFIED = "ALL_REQUIREMENTS_VERIFIED"
    SOME_REQUIREMENTS_VERIFIED = "SOME_REQUIREMENTS_VERIFIED"
    DEVELOPMENT_RECORDS_ONLY = "DEVELOPMENT_RECORDS_ONLY"
    NO_VERIFIED_EVIDENCE = "NO_VERIFIED_EVIDENCE"


@dataclass(frozen=True, slots=True)
class EvidenceAlignmentSummary:
    rule_version: str
    outcome: EvidenceAlignmentOutcome
    triggered_rule: str
    total_requirements: int
    verified_count: int
    learning_target_count: int
    studying_count: int
    no_match_count: int
    explicit_no_evidence_count: int
    no_current_evidence_count: int
    review_required_count: int
    unresolved_requirement_indexes: tuple[int, ...]
    per_requirement_results: tuple[RequirementMatchResult, ...]


def summarise_evidence_alignment(
    results: tuple[RequirementMatchResult, ...],
) -> EvidenceAlignmentSummary:
    verified_count = 0
    learning_target_count = 0
    studying_count = 0
    no_match_count = 0
    explicit_no_evidence_count = 0
    review_required_count = 0
    unresolved_indexes: list[int] = []

    for result in results:
        pair = (result.classification, result.match_basis)
        if pair not in _VALID_PAIRS:
            review_required_count += 1
            unresolved_indexes.append(result.requirement_index)
            continue

        if result.classification == RequirementClassification.REVIEW_REQUIRED:
            review_required_count += 1
            unresolved_indexes.append(result.requirement_index)
            continue

        if result.classification == RequirementClassification.VERIFIED_MATCH:
            verified_count += 1
        elif result.classification == RequirementClassification.LEARNING_TARGET_MATCH:
            learning_target_count += 1
        elif result.classification == RequirementClassification.STUDYING_MATCH:
            studying_count += 1
        elif result.classification == RequirementClassification.NO_EVIDENCE_GAP:
            if result.match_basis == MatchBasis.NO_MATCH:
                no_match_count += 1
            else:
                explicit_no_evidence_count += 1

    total_requirements = len(results)
    no_current_evidence_count = no_match_count + explicit_no_evidence_count
    unresolved_requirement_indexes = tuple(unresolved_indexes)

    if total_requirements == 0:
        outcome = EvidenceAlignmentOutcome.NO_ACCEPTED_REQUIREMENTS
        triggered_rule = "rule_1_no_accepted_requirements"
    elif review_required_count > 0:
        outcome = EvidenceAlignmentOutcome.MANUAL_REVIEW_REQUIRED
        triggered_rule = "rule_2_review_required_or_malformed_present"
    elif verified_count == total_requirements:
        outcome = EvidenceAlignmentOutcome.ALL_REQUIREMENTS_VERIFIED
        triggered_rule = "rule_3_all_requirements_verified"
    elif verified_count > 0:
        outcome = EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED
        triggered_rule = "rule_4_some_requirements_verified"
    elif verified_count == 0 and learning_target_count + studying_count > 0:
        outcome = EvidenceAlignmentOutcome.DEVELOPMENT_RECORDS_ONLY
        triggered_rule = "rule_5_development_records_only"
    else:
        outcome = EvidenceAlignmentOutcome.NO_VERIFIED_EVIDENCE
        triggered_rule = "rule_6_no_verified_evidence"

    return EvidenceAlignmentSummary(
        rule_version=RULE_VERSION,
        outcome=outcome,
        triggered_rule=triggered_rule,
        total_requirements=total_requirements,
        verified_count=verified_count,
        learning_target_count=learning_target_count,
        studying_count=studying_count,
        no_match_count=no_match_count,
        explicit_no_evidence_count=explicit_no_evidence_count,
        no_current_evidence_count=no_current_evidence_count,
        review_required_count=review_required_count,
        unresolved_requirement_indexes=unresolved_requirement_indexes,
        per_requirement_results=results,
    )
