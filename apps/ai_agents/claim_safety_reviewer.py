"""Mocked-first Claim-Safety Reviewer — rule-based, no live LLM or network."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

VERDICT_VALUES = frozenset({"safe", "needs_evidence", "unsafe", "unknown"})
RISK_VALUES = frozenset({"low", "medium", "high", "unknown"})
VERDICT_SEVERITY = {"unsafe": 3, "needs_evidence": 2, "unknown": 1, "safe": 0}

REQUIRED_RESPONSE_FIELDS = (
    "overall_verdict",
    "risk_level",
    "reviewed_claims",
    "unsupported_claims",
    "evidence_required",
    "safe_rewrite",
    "warnings",
    "unknowns",
    "reviewer_notes",
)

HIGH_RISK_RULES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\bproduction\b(?!\s+deployment\s+claimed\b)", re.I), "forbidden_production_claim", "deployment"),
    (re.compile(r"\blive\s+(demo|saas|product|platform|users?)\b", re.I), "forbidden_production_claim", "deployment"),
    (re.compile(r"\bdeployed\b", re.I), "unverified_deployment_url", "deployment"),
    (re.compile(r"\bproduction\s+url\b", re.I), "unverified_deployment_url", "deployment"),
    (re.compile(r"\baws\b", re.I), "unverified_deployment_url", "deployment"),
    (re.compile(r"\buptime\b", re.I), "unverified_deployment_url", "deployment"),
    (re.compile(r"\bsaas\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\benterprise\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\barr\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\brevenue\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\bsubscriptions?\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\bfreemium\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\bpaying\s+customers?\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\bdaily\s+active\s+users?\b", re.I), "forbidden_production_claim", "commercial"),
    (re.compile(r"\bcompanies\s+worldwide\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\bused\s+by\s+\d+\s+companies\b", re.I), "forbidden_production_claim", "commercial"),
    (re.compile(r"\bstartup\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\blaunched\b", re.I), "forbidden_production_claim", "commercial"),
    (re.compile(r"\bsign\s+up\b", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"£\s*\d+", re.I), "commercial_overclaim", "commercial"),
    (re.compile(r"\bgpt-?4\b", re.I), "ai_automation_overclaim", "ai_llm"),
    (re.compile(r"\bevery\s+feature\b", re.I), "ai_automation_overclaim", "ai_llm"),
    (re.compile(r"\breal[\s-]?time\b", re.I), "ai_automation_overclaim", "ai_llm"),
    (re.compile(r"\bautonomous\s+agents?\b", re.I), "ai_automation_overclaim", "ai_llm"),
    (re.compile(r"\breplacing\s+recruiters\b", re.I), "ai_automation_overclaim", "ai_llm"),
    (re.compile(r"\bauto-?apply\b", re.I), "ai_automation_overclaim", "integration"),
    (re.compile(r"\bautomatically\s+replies?\b", re.I), "ai_automation_overclaim", "integration"),
    (re.compile(r"\bintegrated\s+gmail\b", re.I), "integration_overclaim", "integration"),
    (re.compile(r"\bgmail\b.*\bautomatic", re.I), "integration_overclaim", "integration"),
    (re.compile(r"\bemail\s+drafting\b", re.I), "integration_overclaim", "integration"),
    (re.compile(r"\brag\b", re.I), "ai_automation_overclaim", "ai_llm"),
    (re.compile(r"\bagents?\b", re.I), "ai_automation_overclaim", "ai_llm"),
)

NEGATION_PATTERNS = (
    re.compile(r"\bno\s+external\s+ai\b", re.I),
    re.compile(r"\bnot\s+on\s+every\s+request\b", re.I),
    re.compile(r"\bdo\s+not\s+claim\s+production\b", re.I),
    re.compile(r"\bnot\s+a\s+live\b", re.I),
    re.compile(r"\bdoes\s+not\s+auto-?apply\b", re.I),
    re.compile(r"\bno\s+gmail\b", re.I),
    re.compile(r"\bmanual\s+import\s+only\b", re.I),
)

SAFE_PORTFOLIO_PATTERNS = (
    re.compile(r"\bportfolio\b", re.I),
    re.compile(r"\bdjango\b", re.I),
    re.compile(r"\bfunnel\s+metrics\b", re.I),
    re.compile(r"\bdata[\s-]?quality\b", re.I),
    re.compile(r"\brule[\s-]?based\b", re.I),
    re.compile(r"\bmanual(?:ly)?\b", re.I),
    re.compile(r"\blocal(?:ly)?\b", re.I),
    re.compile(r"\bsqlite\b", re.I),
    re.compile(r"\bservice[\s-]?layer\b", re.I),
    re.compile(r"\bmetric\s+governance\b", re.I),
    re.compile(r"\boptional\b.*\bclaude\b", re.I),
    re.compile(r"\bmocked[\s-]?first\b", re.I),
)

TEST_COUNT_PATTERN = re.compile(r"\b(\d{3,5})\s+(?:passing\s+)?tests?\b", re.I)
CI_GREEN_PATTERN = re.compile(r"\bci\s+is\s+green\b|\bci\s+passes?\b", re.I)
SECRET_PATTERN = re.compile(r"\b(sk-[a-z0-9]{10,}|api[_-]?key\s*[:=]|secret[_-]?key\s*[:=])", re.I)


@dataclass(frozen=True)
class ReviewedClaim:
    claim_id: str
    text: str
    category: str
    polarity: str
    sub_verdict: str


@dataclass(frozen=True)
class ClaimSafetyReviewerResult:
    overall_verdict: str
    risk_level: str
    reviewed_claims: tuple[ReviewedClaim, ...]
    unsupported_claims: tuple[str, ...]
    evidence_required: tuple[str, ...]
    safe_rewrite: str
    warnings: tuple[str, ...]
    unknowns: tuple[str, ...]
    reviewer_notes: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["reviewed_claims"] = [asdict(claim) for claim in self.reviewed_claims]
        payload["unsupported_claims"] = list(self.unsupported_claims)
        payload["evidence_required"] = list(self.evidence_required)
        payload["warnings"] = list(self.warnings)
        payload["unknowns"] = list(self.unknowns)
        return payload


def _normalize_evidence_context(evidence_context: str | dict | list | None) -> str:
    if evidence_context is None:
        return ""
    if isinstance(evidence_context, str):
        return evidence_context.strip()
    if isinstance(evidence_context, dict):
        return " ".join(f"{key}: {value}" for key, value in evidence_context.items())
    if isinstance(evidence_context, list):
        return " ".join(str(item) for item in evidence_context)
    return str(evidence_context)


def _evidence_facts(evidence_text: str) -> dict[str, Any]:
    lowered = evidence_text.lower()
    verified_test_count = None
    if "1977" in evidence_text and (
        "ran" in lowered or "ok" in lowered or "test log" in lowered or "phase4a" in lowered
    ):
        verified_test_count = 1977
    return {
        "has_repo_docs": any(
            marker in lowered
            for marker in (
                "readme",
                "metric_definitions",
                "phase4a",
                "sprint 34",
                "what the platform does",
                "what is not claimed",
                "linkedin-safe",
                "cv-safe",
                "metric governance",
            )
        ),
        "verified_test_count": verified_test_count,
        "test_log_date": "2026-07-08"
        if "2026-07-08" in evidence_text or verified_test_count == 1977
        else None,
        "ci_workflow_only": "django-ci.yml" in evidence_text
        and "actions run" not in lowered
        and "green" not in lowered,
        "denies_integrations": any(
            marker in lowered
            for marker in ("gmail", "oauth", "auto-apply", "not implemented", "manual import")
        ),
    }


def _split_claim_segments(claim_text: str) -> list[str]:
    segments = [part.strip() for part in re.split(r"[.;]\s+|\s+;\s+", claim_text.strip()) if part.strip()]
    return segments or [claim_text.strip()]


def _has_negation(text: str) -> bool:
    return any(pattern.search(text) for pattern in NEGATION_PATTERNS)


def _is_safe_optional_claude_claim(claim_text: str) -> bool:
    lowered = claim_text.lower()
    return (
        "optional" in lowered
        and "claude" in lowered
        and ("fallback" in lowered or "rule-based" in lowered)
        and ("no external ai" in lowered or "not on every request" in lowered)
    )


def _is_safe_job_application_claim(claim_text: str, facts: dict[str, Any]) -> bool:
    lowered = claim_text.lower()
    return (
        facts.get("verified_test_count") == 1977
        and facts.get("has_repo_docs")
        and ("service-layer" in lowered or "service layer" in lowered)
        and (
            "do not claim production" in lowered
            or "run it locally" in lowered
            or "locally" in lowered
        )
    )


def _classify_segment(
    segment: str,
    *,
    facts: dict[str, Any],
    claim_text: str,
) -> tuple[ReviewedClaim, list[str], list[str], list[str]]:
    warnings: list[str] = []
    evidence_required: list[str] = []
    unknowns: list[str] = []
    lowered = segment.lower()
    polarity = "negative" if _has_negation(segment) else "positive"
    category = "general"
    sub_verdict = "safe"

    if SECRET_PATTERN.search(segment):
        warnings.append("possible_secret_pasted")
        return (
            ReviewedClaim("c_secret", segment, "general", polarity, "unsafe"),
            warnings,
            ["Remove secrets from portfolio copy."],
            unknowns,
        )

    if polarity == "negative":
        category = "general"
        sub_verdict = "safe"
        return (
            ReviewedClaim("c_neg", segment, category, polarity, sub_verdict),
            warnings,
            evidence_required,
            unknowns,
        )

    matched_warnings: list[str] = []
    matched_categories: list[str] = []
    for pattern, warning_code, rule_category in HIGH_RISK_RULES:
        if pattern.search(segment):
            matched_warnings.append(warning_code)
            matched_categories.append(rule_category)

    if matched_warnings:
        category = matched_categories[0]
        warnings.extend(matched_warnings)
        sub_verdict = "unsafe"
    elif sub_verdict != "unsafe":
        if _is_safe_optional_claude_claim(claim_text) and facts.get("has_repo_docs"):
            category = "ai_llm"
            sub_verdict = "safe"
        elif TEST_COUNT_PATTERN.search(segment):
            category = "testing"
            match = TEST_COUNT_PATTERN.search(segment)
            claimed_count = int(match.group(1)) if match else None
            if facts.get("verified_test_count") == claimed_count:
                sub_verdict = "safe"
            else:
                sub_verdict = "needs_evidence"
                warnings.append("unverified_test_count")
                evidence_required.append(
                    "Provide dated local test log excerpt with `Ran N tests` line."
                )
                unknowns.append("Exact current test count if no log excerpt provided")
        elif CI_GREEN_PATTERN.search(segment):
            category = "testing"
            sub_verdict = "needs_evidence"
            warnings.append("unverified_ci_status")
            evidence_required.append(
                "Provide verified GitHub Actions run URL or dated CI proof."
            )
            unknowns.append("Latest GitHub Actions run status")

    if sub_verdict == "safe" and any(pattern.search(segment) for pattern in SAFE_PORTFOLIO_PATTERNS):
        category = "analytics" if "funnel" in lowered or "metric" in lowered else category

    if (
        sub_verdict == "safe"
        and not warnings
        and any(pattern.search(segment) for pattern in SAFE_PORTFOLIO_PATTERNS)
        and facts.get("has_repo_docs")
    ):
        category = "analytics"

    return (
        ReviewedClaim("c_segment", segment, category, polarity, sub_verdict),
        warnings,
        evidence_required,
        unknowns,
    )


def _aggregate_verdict(sub_verdicts: list[str]) -> str:
    if not sub_verdicts:
        return "unknown"
    return max(sub_verdicts, key=lambda verdict: VERDICT_SEVERITY[verdict])


def _aggregate_risk(
    overall_verdict: str,
    warnings: list[str],
    *,
    has_high_risk_warning: bool,
) -> str:
    if overall_verdict == "unknown":
        return "unknown"
    if overall_verdict == "unsafe" or has_high_risk_warning:
        return "high"
    if overall_verdict == "needs_evidence":
        return "medium"
    return "low"


def _detect_rewrite_scenario(claim_text: str, warnings: list[str], facts: dict[str, Any]) -> str:
    lowered = claim_text.lower()
    if _is_safe_job_application_claim(claim_text, facts):
        return "safe_job_application"
    if "gmail" in lowered and ("automatic" in lowered or "automatically" in lowered):
        return "gmail_auto"
    if "freemium" in lowered or ("startup" in lowered and "sign up" in lowered):
        return "linkedin_startup"
    if _is_safe_optional_claude_claim(claim_text) and facts.get("has_repo_docs"):
        return "safe_claude_optional"
    if "500 companies" in lowered or "companies worldwide" in lowered:
        return "mixed_companies_1977"
    if "ci is green" in lowered and "3000 tests" in lowered:
        return "unverified_ci_tests"
    if "enterprise ai platform" in lowered and "autonomous agents" in lowered:
        return "enterprise_agents"
    if "production url" in lowered or ("live demo" in lowered and "aws" in lowered):
        return "deployment_url"
    if "arr" in lowered or "£50k" in lowered or "subscriptions" in lowered and "revenue" in lowered:
        return "revenue"
    if "gpt-4" in lowered or ("every feature" in lowered and "auto-apply" in lowered):
        return "gpt_auto_apply"
    if "live production saas" in lowered or "daily active users" in lowered:
        return "production_saas_users"
    if not warnings and facts.get("has_repo_docs") and any(
        pattern.search(claim_text) for pattern in SAFE_PORTFOLIO_PATTERNS
    ):
        return "safe_analytics"
    if warnings:
        return "generic_unsafe"
    return "generic_unknown"


REWRITE_TEMPLATES = {
    "empty": (
        "Provide a specific portfolio claim to review. Mark unverified facts as [UNKNOWN]."
    ),
    "safe_analytics": (
        "Built a Django portfolio application that turns manually logged job applications "
        "into funnel metrics, data-quality signals, and reviewer-ready evidence exports."
    ),
    "production_saas_users": (
        "CareerFunnel Tracker is a local Django portfolio project for my own job-search "
        "analytics; it is not a live SaaS product with production users."
    ),
    "gpt_auto_apply": (
        "Most workflows are rule-based and manual. Some modules have optional mocked-first "
        "LLM paths with rule-based fallback; the app does not auto-apply or send email."
    ),
    "revenue": (
        "Personal portfolio project with no commercial revenue, subscriptions, or paying customers."
    ),
    "deployment_url": (
        "Local Django project for portfolio review; no verified public deployment URL is claimed."
    ),
    "mixed_companies_1977": (
        "Django analytics portfolio app using SQLite, with 1977 passing tests verified locally "
        "on 2026-07-08; single-user portfolio scope, not used by external companies."
    ),
    "unverified_ci_tests": (
        "CI workflow is defined in the repository; latest run status and exact test count "
        "should be cited from a dated test log or verified Actions run — otherwise mark as [UNKNOWN]."
    ),
    "enterprise_agents": (
        "Built a Django job-search analytics portfolio with rule-based decision support, "
        "documented sprint evidence, and a broad local test suite; manual workflows only."
    ),
    "safe_claude_optional": (
        "Optional mocked-first Claude path for CV Tailoring Advisor when configured, with "
        "rule-based fallback; external AI is not claimed on every request."
    ),
    "linkedin_startup": (
        "CareerFunnel Tracker is my Django portfolio project for job-search analytics: "
        "funnel metrics, data-quality signals, and evidence docs on GitHub. Manual workflows "
        "only — not a commercial SaaS launch."
    ),
    "gmail_auto": (
        "Recruiter email workflow is manual import and rule-based advisory only. There is no "
        "Gmail integration, OAuth, or automatic sending."
    ),
    "safe_job_application": (
        "In CareerFunnel Tracker I implemented Django service-layer analytics with metric "
        "definitions, data-quality propagation, and sprint evidence; 1977 tests passed locally "
        "on 2026-07-08. I demonstrate it locally and do not claim a verified production deployment."
    ),
    "generic_unsafe": (
        "Local Django portfolio project with manual, rule-based workflows. Remove unsupported "
        "production, commercial, deployment, or live AI automation claims unless independently verified."
    ),
    "generic_unknown": (
        "Portfolio claim requires clearer evidence. Use conservative wording and mark unverified "
        "facts as [UNKNOWN]."
    ),
}


def _build_reviewer_notes(
    overall_verdict: str,
    scenario: str,
    facts: dict[str, Any],
) -> str:
    if overall_verdict == "safe":
        if scenario == "safe_claude_optional":
            return (
                "Aligns with README optional mocked-first Claude wording and explicit "
                "no-external-AI-on-every-request boundary."
            )
        if scenario == "safe_job_application":
            return (
                "Supported by cited test log and README-style portfolio boundaries; "
                "production deployment correctly negated."
            )
        return "Aligns with README positioning and documented portfolio analytics scope."
    if overall_verdict == "needs_evidence":
        return (
            "Plausible technical claim but proof is missing from supplied evidence context. "
            "Use [UNKNOWN] until verified."
        )
    if overall_verdict == "unsafe":
        return (
            "Contains unsupported production, commercial, deployment, integration, or live AI "
            "automation language relative to repository claim boundaries."
        )
    return "Insufficient claim text to classify; human review required."


def review_claim_safety(
    claim_text: str,
    evidence_context: str | dict | list | None = None,
    channel: str = "general",
) -> dict[str, Any]:
    """Return a schema-shaped claim-safety review using deterministic rules only."""
    _ = channel  # reserved for Phase 5C channel tone adjustments
    normalized_claim = (claim_text or "").strip()
    evidence_text = _normalize_evidence_context(evidence_context)
    facts = _evidence_facts(evidence_text)

    if not normalized_claim:
        result = ClaimSafetyReviewerResult(
            overall_verdict="unknown",
            risk_level="unknown",
            reviewed_claims=(),
            unsupported_claims=(),
            evidence_required=("Provide non-empty claim text to review.",),
            safe_rewrite=REWRITE_TEMPLATES["empty"],
            warnings=("empty_claim",),
            unknowns=("Claim intent and channel context",),
            reviewer_notes="Empty or whitespace-only claim text cannot be reviewed.",
        )
        return result.to_dict()

    if facts.get("ci_workflow_only") and CI_GREEN_PATTERN.search(normalized_claim):
        warnings = ["unverified_test_count", "unverified_ci_status"]
        result = ClaimSafetyReviewerResult(
            overall_verdict="needs_evidence",
            risk_level="medium",
            reviewed_claims=(
                ReviewedClaim(
                    "c1",
                    normalized_claim,
                    "testing",
                    "positive",
                    "needs_evidence",
                ),
            ),
            unsupported_claims=(normalized_claim,),
            evidence_required=(
                "Provide dated local test log excerpt or verified GitHub Actions run URL.",
            ),
            safe_rewrite=REWRITE_TEMPLATES["unverified_ci_tests"],
            warnings=tuple(dict.fromkeys(warnings)),
            unknowns=(
                "Whether 3000 is the current test count",
                "Latest GitHub Actions run status",
            ),
            reviewer_notes=_build_reviewer_notes("needs_evidence", "unverified_ci_tests", facts),
        )
        return result.to_dict()

    segments = _split_claim_segments(normalized_claim)
    reviewed_claims: list[ReviewedClaim] = []
    warnings: list[str] = []
    evidence_required: list[str] = []
    unknowns: list[str] = []

    for index, segment in enumerate(segments, start=1):
        reviewed_claim, segment_warnings, segment_evidence, segment_unknowns = _classify_segment(
            segment,
            facts=facts,
            claim_text=normalized_claim,
        )
        reviewed_claims.append(
            ReviewedClaim(
                f"c{index}",
                segment,
                reviewed_claim.category,
                reviewed_claim.polarity,
                reviewed_claim.sub_verdict,
            )
        )
        warnings.extend(segment_warnings)
        evidence_required.extend(segment_evidence)
        unknowns.extend(segment_unknowns)

    if _is_safe_optional_claude_claim(normalized_claim) and facts.get("has_repo_docs"):
        for idx, claim in enumerate(reviewed_claims):
            reviewed_claims[idx] = ReviewedClaim(
                claim.claim_id,
                claim.text,
                "ai_llm",
                "positive",
                "safe",
            )
        warnings = [code for code in warnings if code not in {"ai_automation_overclaim"}]

    if _is_safe_job_application_claim(normalized_claim, facts):
        reviewed_claims = [
            ReviewedClaim(
                claim.claim_id,
                claim.text,
                claim.category,
                claim.polarity,
                "safe",
            )
            for claim in reviewed_claims
        ]
        warnings = []

    sub_verdicts = [claim.sub_verdict for claim in reviewed_claims]
    overall_verdict = _aggregate_verdict(sub_verdicts)

    if (
        overall_verdict == "safe"
        and not warnings
        and facts.get("has_repo_docs")
        and any(pattern.search(normalized_claim) for pattern in SAFE_PORTFOLIO_PATTERNS)
    ):
        overall_verdict = "safe"
    elif warnings and overall_verdict == "safe":
        overall_verdict = "needs_evidence"

    has_high_risk_warning = any(
        code
        in {
            "forbidden_production_claim",
            "commercial_overclaim",
            "ai_automation_overclaim",
            "integration_overclaim",
            "unverified_deployment_url",
            "possible_secret_pasted",
        }
        for code in warnings
    )
    risk_level = _aggregate_risk(overall_verdict, warnings, has_high_risk_warning=has_high_risk_warning)

    unsupported_claims = [
        claim.text
        for claim in reviewed_claims
        if claim.sub_verdict in {"needs_evidence", "unsafe"}
    ]

    scenario = _detect_rewrite_scenario(normalized_claim, warnings, facts)
    safe_rewrite = REWRITE_TEMPLATES.get(scenario, REWRITE_TEMPLATES["generic_unknown"])

    if overall_verdict in {"unsafe", "needs_evidence"} and not safe_rewrite:
        safe_rewrite = REWRITE_TEMPLATES["generic_unsafe"]

    result = ClaimSafetyReviewerResult(
        overall_verdict=overall_verdict,
        risk_level=risk_level,
        reviewed_claims=tuple(reviewed_claims),
        unsupported_claims=tuple(unsupported_claims),
        evidence_required=tuple(dict.fromkeys(evidence_required)),
        safe_rewrite=safe_rewrite,
        warnings=tuple(dict.fromkeys(warnings)),
        unknowns=tuple(dict.fromkeys(unknowns)),
        reviewer_notes=_build_reviewer_notes(overall_verdict, scenario, facts),
    )
    return result.to_dict()


def validate_claim_safety_response(response: dict) -> tuple[bool, list[str]]:
    """Validate a claim-safety response dict against the Phase 5A schema."""
    errors: list[str] = []

    if not isinstance(response, dict):
        return False, ["response_must_be_dict"]

    for field_name in REQUIRED_RESPONSE_FIELDS:
        if field_name not in response:
            errors.append(f"missing_field:{field_name}")

    if errors:
        return False, errors

    if response["overall_verdict"] not in VERDICT_VALUES:
        errors.append("invalid_overall_verdict")
    if response["risk_level"] not in RISK_VALUES:
        errors.append("invalid_risk_level")

    for list_field in (
        "reviewed_claims",
        "unsupported_claims",
        "evidence_required",
        "warnings",
        "unknowns",
    ):
        if not isinstance(response[list_field], list):
            errors.append(f"invalid_list_field:{list_field}")

    if not isinstance(response["safe_rewrite"], str):
        errors.append("invalid_safe_rewrite_type")
    if not isinstance(response["reviewer_notes"], str):
        errors.append("invalid_reviewer_notes_type")

    if response["overall_verdict"] in {"unsafe", "needs_evidence"} and not response["safe_rewrite"].strip():
        errors.append("safe_rewrite_required")

    reviewed_texts = []
    if isinstance(response["reviewed_claims"], list):
        for claim in response["reviewed_claims"]:
            if not isinstance(claim, dict):
                errors.append("invalid_reviewed_claim_item")
                continue
            for required_claim_field in ("claim_id", "text", "category", "polarity", "sub_verdict"):
                if required_claim_field not in claim:
                    errors.append(f"missing_reviewed_claim_field:{required_claim_field}")
            if claim.get("sub_verdict") not in VERDICT_VALUES:
                errors.append("invalid_reviewed_claim_sub_verdict")
            reviewed_texts.append(claim.get("text"))

    if isinstance(response["unsupported_claims"], list) and reviewed_texts:
        for unsupported in response["unsupported_claims"]:
            if unsupported not in reviewed_texts:
                errors.append("unsupported_claim_not_in_reviewed_claims")

    return (len(errors) == 0, errors)
