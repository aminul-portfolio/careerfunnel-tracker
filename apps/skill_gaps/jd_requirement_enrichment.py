from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

MIN_EXCERPT_LENGTH = 5
MAX_EXCERPT_LENGTH = 300
ALLOWED_CONFIDENCE_LEVELS = {"high", "medium", "low"}
ALLOWED_PROVENANCE_VALUES = {"llm_candidate", "rule_based", "both"}

REQUIRED_ENRICHMENT_SAFETY_WORDING = (
    "Requirement enrichment is advisory only.",
    "Candidate requirements are extracted for planning review only.",
    "Deterministic tracked terms remain unchanged.",
    (
        "A candidate requirement does not mean the skill is verified, claim-ready, "
        "or required by every employer."
    ),
    "Review the saved job description before using any suggestion.",
    (
        "Each candidate requirement includes an exact excerpt from your saved job "
        "description. Excerpts that could not be verified were rejected automatically."
    ),
)

ENRICHMENT_CANDIDATE_FIELDS = {
    "term",
    "excerpt",
    "confidence",
    "provenance",
    "is_excerpt_verified",
    "rejection_reason",
}

PROFICIENCY_CLAIM_TERMS = (
    "proficient",
    "expert",
    "mastery",
    "verified proficiency",
    "production-ready",
)

EMPLOYER_READINESS_TERMS = (
    "employer-ready",
    "employer ready",
    "meets employer requirement",
    "meets a specific employer requirement",
    "required by every employer",
)

SALARY_OR_CONTACT_TERMS = (
    "salary",
    "compensation",
    "contact",
    "email",
    "phone",
    "recruiter",
)

CLAIM_READY_TERMS = (
    "claim-ready",
    "claim ready",
    "ready to claim",
    "cv-ready",
    "interview-ready",
)

JOB_OUTCOME_TERMS = (
    "offer prediction",
    "interview prediction",
    "hiring outcome",
    "will get hired",
)

MOCKED_TERM_HINTS = (
    "python",
    "sql",
    "power bi",
    "tableau",
    "snowflake",
    "dbt",
    "airflow",
    "excel",
    "dashboard",
    "stakeholder",
)


@dataclass(frozen=True)
class EnrichmentCandidate:
    term: str
    excerpt: str
    confidence: str
    provenance: str
    is_excerpt_verified: bool
    rejection_reason: str | None = None


class EnrichmentCandidateValidationError(ValueError):
    """Raised when a candidate does not satisfy the strict contract schema."""


def normalise_jd_text(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def excerpt_is_verified(excerpt: str, jd_text: str) -> bool:
    normalised_excerpt = normalise_jd_text(excerpt)
    if not (MIN_EXCERPT_LENGTH <= len(normalised_excerpt) <= MAX_EXCERPT_LENGTH):
        return False
    normalised_jd = normalise_jd_text(jd_text)
    return normalised_excerpt.lower() in normalised_jd.lower()


def sanitise_jd_text_for_enrichment(jd_text: str) -> str:
    text = str(jd_text or "")
    text = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "", text)
    text = re.sub(r"https?://\S+|www\.\S+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)", "", text)
    return normalise_jd_text(text)


def _raise_schema_error(reason: str) -> None:
    raise EnrichmentCandidateValidationError(reason)


def _schema_validated_candidate(candidate: dict[str, Any]) -> EnrichmentCandidate:
    keys = set(candidate)
    missing_fields = ENRICHMENT_CANDIDATE_FIELDS - keys
    extra_fields = keys - ENRICHMENT_CANDIDATE_FIELDS
    if missing_fields:
        _raise_schema_error("missing_required_fields")
    if extra_fields:
        _raise_schema_error("extra_schema_keys")

    term = normalise_jd_text(candidate["term"])
    excerpt = normalise_jd_text(candidate["excerpt"])
    confidence = normalise_jd_text(candidate["confidence"]).lower()
    provenance = normalise_jd_text(candidate["provenance"]).lower()
    is_excerpt_verified = candidate["is_excerpt_verified"]
    rejection_reason = candidate["rejection_reason"]

    if not term:
        _raise_schema_error("empty_term")
    if not excerpt:
        _raise_schema_error("empty_excerpt")
    if confidence not in ALLOWED_CONFIDENCE_LEVELS:
        _raise_schema_error("invalid_confidence")
    if provenance not in ALLOWED_PROVENANCE_VALUES:
        _raise_schema_error("invalid_provenance")
    if not isinstance(is_excerpt_verified, bool):
        _raise_schema_error("invalid_excerpt_verification_flag")
    if rejection_reason is not None and not isinstance(rejection_reason, str):
        _raise_schema_error("invalid_rejection_reason")

    return EnrichmentCandidate(
        term=term,
        excerpt=excerpt,
        confidence=confidence,
        provenance=provenance,
        is_excerpt_verified=is_excerpt_verified,
        rejection_reason=normalise_jd_text(rejection_reason) if rejection_reason else None,
    )


def _candidate_with_rejection(
    candidate: EnrichmentCandidate,
    rejection_reason: str,
) -> EnrichmentCandidate:
    return EnrichmentCandidate(
        term=candidate.term,
        excerpt=candidate.excerpt,
        confidence=candidate.confidence,
        provenance=candidate.provenance,
        is_excerpt_verified=False,
        rejection_reason=rejection_reason,
    )


def _claim_safety_rejection_reason(candidate: EnrichmentCandidate) -> str | None:
    text = f"{candidate.term} {candidate.excerpt}".lower()
    if any(term in text for term in SALARY_OR_CONTACT_TERMS):
        return "salary_or_contact_term"
    if any(term in text for term in PROFICIENCY_CLAIM_TERMS):
        return "proficiency_claim"
    if any(term in text for term in EMPLOYER_READINESS_TERMS):
        return "employer_readiness_claim"
    if any(term in text for term in CLAIM_READY_TERMS):
        return "claim_ready_implication"
    if any(term in text for term in JOB_OUTCOME_TERMS):
        return "employer_readiness_claim"
    return None


def validate_enrichment_candidate(
    candidate: dict[str, Any],
    *,
    jd_text: str,
) -> EnrichmentCandidate:
    validated_candidate = _schema_validated_candidate(candidate)

    claim_safety_reason = _claim_safety_rejection_reason(validated_candidate)
    if claim_safety_reason:
        return _candidate_with_rejection(validated_candidate, claim_safety_reason)
    if not validated_candidate.is_excerpt_verified:
        return _candidate_with_rejection(
            validated_candidate,
            "invalid_excerpt_verification_flag",
        )
    if not excerpt_is_verified(validated_candidate.excerpt, jd_text):
        return _candidate_with_rejection(validated_candidate, "excerpt_not_found_in_jd")
    return validated_candidate


def validate_enrichment_candidates(
    candidates: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    jd_text: str,
) -> tuple[EnrichmentCandidate, ...]:
    accepted_candidates: list[EnrichmentCandidate] = []
    for candidate in candidates:
        validated_candidate = validate_enrichment_candidate(candidate, jd_text=jd_text)
        if validated_candidate.rejection_reason is None:
            accepted_candidates.append(validated_candidate)
    return tuple(accepted_candidates)


def _candidate_dict(
    *,
    term: str,
    excerpt: str,
    confidence: str = "medium",
    provenance: str = "rule_based",
) -> dict[str, Any]:
    return {
        "term": term,
        "excerpt": excerpt,
        "confidence": confidence,
        "provenance": provenance,
        "is_excerpt_verified": True,
        "rejection_reason": None,
    }


def _sentences_from_jd(jd_text: str) -> tuple[str, ...]:
    text = sanitise_jd_text_for_enrichment(jd_text)
    return tuple(
        sentence
        for sentence in (normalise_jd_text(part) for part in re.split(r"[.;\n]+", text))
        if MIN_EXCERPT_LENGTH <= len(sentence) <= MAX_EXCERPT_LENGTH
    )


def build_mocked_enrichment_candidates(jd_text: str) -> tuple[EnrichmentCandidate, ...]:
    candidate_dicts: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    for sentence in _sentences_from_jd(jd_text):
        lowered_sentence = sentence.lower()
        if _claim_safety_rejection_reason(
            EnrichmentCandidate("", sentence, "low", "rule_based", True),
        ):
            continue
        for term in MOCKED_TERM_HINTS:
            if term in seen_terms:
                continue
            if term in lowered_sentence:
                candidate_dicts.append(
                    _candidate_dict(term=term, excerpt=sentence, confidence="medium"),
                )
                seen_terms.add(term)
                break
    return validate_enrichment_candidates(tuple(candidate_dicts), jd_text=jd_text)


def build_enrichment_prompt_payload(
    *,
    jd_text: str,
    tracked_terms: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "instructions": list(REQUIRED_ENRICHMENT_SAFETY_WORDING),
        "jd_text": sanitise_jd_text_for_enrichment(jd_text),
        "tracked_terms": [
            term
            for term in (normalise_jd_text(value) for value in tracked_terms)
            if term
        ],
    }
