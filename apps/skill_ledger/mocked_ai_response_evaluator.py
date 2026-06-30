from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

from apps.skill_ledger.ai_explanation import (
    FORBIDDEN_EXPLANATION_PHRASES,
    REQUIRED_EXPLANATION_SAFETY_WARNING,
)

EVALUATION_FORBIDDEN_PHRASES = FORBIDDEN_EXPLANATION_PHRASES + (
    "your cv has been updated",
    "your linkedin has been updated",
    "your profile has been updated",
    "your application has been submitted",
    "your skill ledger has been updated",
    "skill verified by this analysis",
    "evidence level has been changed",
    "this confirms you are proficient",
)

LEARNING_TARGET_INFLATION = "learning_target_presented_as_verified"
JD_SIGNAL_AS_PROFICIENCY = "jd_signal_presented_as_proficiency"
MUTATION_CLAIM_DETECTED = "mutation_claim_detected"
GENERATED_DOCUMENT_DETECTED = "generated_document_detected"
AUTO_ACTION_DETECTED = "auto_action_detected"
CERTIFICATION_GUARANTEE = "certification_guarantee"
EMPLOYER_OUTCOME_PREDICTION = "employer_outcome_prediction"
LIVE_PROVIDER_IMPLICATION = "live_provider_implication"
EMPTY_RESPONSE = "empty_response"

_EVALUATED_AT_SPRINT = "sprint_101"

_PROFICIENCY_TERMS = r"(?:verified|proficient|expert|claim[\s-]?ready|proven)"
_LEARNING_CONTEXT = r"(?:learning[\s-]target|studying|no[\s-]evidence)"

_LEARNING_TARGET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            rf"{_LEARNING_CONTEXT}.{{0,60}}{_PROFICIENCY_TERMS}|"
            rf"{_PROFICIENCY_TERMS}.{{0,60}}{_LEARNING_CONTEXT}",
            re.IGNORECASE,
        ),
        LEARNING_TARGET_INFLATION,
    ),
)

_JD_SIGNAL_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"(?:jd[\s-]signal|job[\s-]description|job[\s-]posting|requirement)"
            r".{0,40}(?:proves?|confirms?|verif(?:y|ies)|demonstrates?)"
            r"|(?:proves?|confirms?|verif(?:y|ies)|demonstrates?)"
            r".{0,40}(?:jd[\s-]signal|job[\s-]description|job[\s-]posting|requirement)",
            re.IGNORECASE,
        ),
        JD_SIGNAL_AS_PROFICIENCY,
    ),
    (
        re.compile(
            r"(?:jd[\s-]signal|job[\s-]description|job[\s-]posting|requirement)"
            r".{0,40}(?:you\s+(?:have|are)|(?:is|are)\s+proficient)",
            re.IGNORECASE,
        ),
        JD_SIGNAL_AS_PROFICIENCY,
    ),
)

_MUTATION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"updated\s+your\s+cv", re.IGNORECASE), MUTATION_CLAIM_DETECTED),
    (re.compile(r"saved\s+to\s+your\s+skill\s+ledger", re.IGNORECASE), MUTATION_CLAIM_DETECTED),
    (re.compile(r"added\s+to\s+your\s+linkedin", re.IGNORECASE), MUTATION_CLAIM_DETECTED),
    (re.compile(r"submitted\s+your\s+application", re.IGNORECASE), MUTATION_CLAIM_DETECTED),
    (re.compile(r"sent\s+your\s+email", re.IGNORECASE), MUTATION_CLAIM_DETECTED),
    (
        re.compile(
            r"(?:updated|saved|added|changed|submitted|sent)\s+(?:your|the)\s+",
            re.IGNORECASE,
        ),
        MUTATION_CLAIM_DETECTED,
    ),
)

_GENERATED_DOCUMENT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"generated\s+your\s+cv", re.IGNORECASE), GENERATED_DOCUMENT_DETECTED),
    (re.compile(r"created\s+your\s+cover\s+letter", re.IGNORECASE), GENERATED_DOCUMENT_DETECTED),
    (re.compile(r"produced\s+a\s+document", re.IGNORECASE), GENERATED_DOCUMENT_DETECTED),
    (
        re.compile(
            r"here\s+is\s+your\s+updated\s+profile",
            re.IGNORECASE,
        ),
        GENERATED_DOCUMENT_DETECTED,
    ),
)

_AUTO_ACTION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"automatically\s+updated", re.IGNORECASE), AUTO_ACTION_DETECTED),
    (re.compile(r"on\s+your\s+behalf", re.IGNORECASE), AUTO_ACTION_DETECTED),
    (re.compile(r"we\s+have\s+updated", re.IGNORECASE), AUTO_ACTION_DETECTED),
    (re.compile(r"the\s+system\s+has\s+submitted", re.IGNORECASE), AUTO_ACTION_DETECTED),
    (re.compile(r"careerfunnel\s+has\s+saved", re.IGNORECASE), AUTO_ACTION_DETECTED),
)

_CERTIFICATION_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"certifies?\s+your\s+proficiency", re.IGNORECASE), CERTIFICATION_GUARANTEE),
    (re.compile(r"confirms?\s+you\s+are\s+proficient", re.IGNORECASE), CERTIFICATION_GUARANTEE),
    (re.compile(r"guarantees?\s+your\s+skill", re.IGNORECASE), CERTIFICATION_GUARANTEE),
    (re.compile(r"verified\s+by\s+this\s+analysis", re.IGNORECASE), CERTIFICATION_GUARANTEE),
)

_EMPLOYER_OUTCOME_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"guarantees?\s+interviews?", re.IGNORECASE), EMPLOYER_OUTCOME_PREDICTION),
    (re.compile(r"employers?\s+will\s+accept", re.IGNORECASE), EMPLOYER_OUTCOME_PREDICTION),
    (re.compile(r"will\s+get\s+you\s+hired", re.IGNORECASE), EMPLOYER_OUTCOME_PREDICTION),
    (re.compile(r"predicts?\s+employer\s+outcomes?", re.IGNORECASE), EMPLOYER_OUTCOME_PREDICTION),
)

_LIVE_PROVIDER_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"openai\s+confirmed", re.IGNORECASE), LIVE_PROVIDER_IMPLICATION),
    (re.compile(r"anthropic\s+confirmed", re.IGNORECASE), LIVE_PROVIDER_IMPLICATION),
    (re.compile(r"gemini\s+confirmed", re.IGNORECASE), LIVE_PROVIDER_IMPLICATION),
    (re.compile(r"the\s+ai\s+provider\s+confirmed", re.IGNORECASE), LIVE_PROVIDER_IMPLICATION),
    (re.compile(r"live\s+ai\s+model\s+verified", re.IGNORECASE), LIVE_PROVIDER_IMPLICATION),
)

_FORBIDDEN_PHRASE_CODE_MAP: dict[str, str] = {
    "this jd signal verifies": JD_SIGNAL_AS_PROFICIENCY,
    "this proves proficiency": CERTIFICATION_GUARANTEE,
    "ai verified": LIVE_PROVIDER_IMPLICATION,
    "automatically verified": AUTO_ACTION_DETECTED,
    "employer confirmed": EMPLOYER_OUTCOME_PREDICTION,
    "you are qualified": CERTIFICATION_GUARANTEE,
    "job ready": CERTIFICATION_GUARANTEE,
    "employer ready": CERTIFICATION_GUARANTEE,
    "skill confirmed": CERTIFICATION_GUARANTEE,
    "ready to apply": CERTIFICATION_GUARANTEE,
    "you meet the requirements": CERTIFICATION_GUARANTEE,
    "proficiency confirmed": CERTIFICATION_GUARANTEE,
    "your cv has been updated": MUTATION_CLAIM_DETECTED,
    "your linkedin has been updated": MUTATION_CLAIM_DETECTED,
    "your profile has been updated": MUTATION_CLAIM_DETECTED,
    "your application has been submitted": MUTATION_CLAIM_DETECTED,
    "your skill ledger has been updated": MUTATION_CLAIM_DETECTED,
    "skill verified by this analysis": CERTIFICATION_GUARANTEE,
    "evidence level has been changed": MUTATION_CLAIM_DETECTED,
    "this confirms you are proficient": CERTIFICATION_GUARANTEE,
}


@dataclass(frozen=True)
class EvaluationFinding:
    code: str
    excerpt: str
    severity: str


@dataclass(frozen=True)
class MockedAIResponseEvaluation:
    verdict: str
    findings: Tuple[EvaluationFinding, ...]
    input_length: int
    evaluated_at_sprint: str


def _extract_excerpt(text: str, match: re.Match[str]) -> str:
    return text[match.start() : match.end()]


def _is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 80) : start].lower()
    negations = (
        "does not ",
        "do not ",
        "did not ",
        "should not ",
        "must not ",
        "cannot ",
        "can't ",
        "not claim ",
        "not present",
        "not be presented",
        "without ",
    )
    return any(negation in prefix for negation in negations)


def _match_contains_internal_negation(match: re.Match[str]) -> bool:
    return bool(re.search(r"\b(?:not|never|without)\b", match.group(0), re.IGNORECASE))


def _find_pattern_matches(
    text: str,
    patterns: tuple[tuple[re.Pattern[str], str], ...],
) -> list[EvaluationFinding]:
    findings: list[EvaluationFinding] = []
    for pattern, code in patterns:
        for match in pattern.finditer(text):
            if _is_negated(text, match.start()) or _match_contains_internal_negation(match):
                continue
            excerpt = _extract_excerpt(text, match)
            if excerpt:
                findings.append(EvaluationFinding(code=code, excerpt=excerpt, severity="block"))
    return findings


def _find_forbidden_phrase_matches(text: str) -> list[EvaluationFinding]:
    findings: list[EvaluationFinding] = []
    lowered = text.lower()
    for phrase in EVALUATION_FORBIDDEN_PHRASES:
        start = 0
        while True:
            index = lowered.find(phrase, start)
            if index == -1:
                break
            excerpt = text[index : index + len(phrase)]
            code = _FORBIDDEN_PHRASE_CODE_MAP.get(phrase, CERTIFICATION_GUARANTEE)
            findings.append(EvaluationFinding(code=code, excerpt=excerpt, severity="block"))
            start = index + len(phrase)
    return findings


def _dedupe_findings(findings: list[EvaluationFinding]) -> tuple[EvaluationFinding, ...]:
    seen: set[tuple[str, str]] = set()
    unique: list[EvaluationFinding] = []
    for finding in findings:
        key = (finding.code, finding.excerpt.lower())
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)
    return tuple(unique)


def _determine_verdict(findings: tuple[EvaluationFinding, ...]) -> str:
    if not findings:
        return "allowed"
    if any(finding.severity == "block" for finding in findings):
        return "blocked"
    return "warning"


def evaluate_mocked_ai_response(response_text: str) -> MockedAIResponseEvaluation:
    findings: list[EvaluationFinding] = []

    if not response_text.strip():
        findings.append(
            EvaluationFinding(
                code=EMPTY_RESPONSE,
                excerpt=response_text if response_text else "(empty)",
                severity="block",
            )
        )
        deduped = _dedupe_findings(findings)
        return MockedAIResponseEvaluation(
            verdict=_determine_verdict(deduped),
            findings=deduped,
            input_length=len(response_text),
            evaluated_at_sprint=_EVALUATED_AT_SPRINT,
        )

    pattern_groups = (
        _LEARNING_TARGET_PATTERNS,
        _JD_SIGNAL_PATTERNS,
        _MUTATION_PATTERNS,
        _GENERATED_DOCUMENT_PATTERNS,
        _AUTO_ACTION_PATTERNS,
        _CERTIFICATION_PATTERNS,
        _EMPLOYER_OUTCOME_PATTERNS,
        _LIVE_PROVIDER_PATTERNS,
    )
    for patterns in pattern_groups:
        findings.extend(_find_pattern_matches(response_text, patterns))

    findings.extend(_find_forbidden_phrase_matches(response_text))

    deduped = _dedupe_findings(findings)
    return MockedAIResponseEvaluation(
        verdict=_determine_verdict(deduped),
        findings=deduped,
        input_length=len(response_text),
        evaluated_at_sprint=_EVALUATED_AT_SPRINT,
    )


__all__ = [
    "AUTO_ACTION_DETECTED",
    "CERTIFICATION_GUARANTEE",
    "EMPLOYER_OUTCOME_PREDICTION",
    "EMPTY_RESPONSE",
    "EVALUATION_FORBIDDEN_PHRASES",
    "EvaluationFinding",
    "GENERATED_DOCUMENT_DETECTED",
    "JD_SIGNAL_AS_PROFICIENCY",
    "LEARNING_TARGET_INFLATION",
    "LIVE_PROVIDER_IMPLICATION",
    "MUTATION_CLAIM_DETECTED",
    "MockedAIResponseEvaluation",
    "REQUIRED_EXPLANATION_SAFETY_WARNING",
    "evaluate_mocked_ai_response",
]
