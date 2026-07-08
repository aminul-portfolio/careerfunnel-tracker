import importlib
import re
from pathlib import Path

from django.test import SimpleTestCase

from apps.ai_agents.claim_safety_reviewer import (
    REQUIRED_RESPONSE_FIELDS,
    RISK_VALUES,
    VERDICT_VALUES,
    review_claim_safety,
    validate_claim_safety_response,
)

MODULE_PATH = Path(__file__).resolve().parent / "claim_safety_reviewer.py"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


GOLDEN_CASES = [
    {
        "name": "case_01_safe_analytics",
        "claim": (
            "Built a Django portfolio application that turns manually logged job applications "
            "into funnel metrics and data-quality warnings."
        ),
        "evidence": (
            'README "What The Platform Does"; '
            "docs/analytics/metric_definitions.md referenced"
        ),
        "channel": "general",
        "expected_verdict": "safe",
        "expected_risk": "low",
        "expected_warnings": [],
        "expected_rewrite": (
            "Built a Django portfolio application that turns manually logged job applications "
            "into funnel metrics, data-quality signals, and reviewer-ready evidence exports."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_02_unsupported_production",
        "claim": (
            "CareerFunnel Tracker is a live production SaaS platform serving hundreds of "
            "daily active users."
        ),
        "evidence": 'README "What Is Not Claimed" — no production users',
        "channel": "general",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["forbidden_production_claim", "commercial_overclaim"],
        "expected_rewrite": (
            "CareerFunnel Tracker is a local Django portfolio project for my own job-search "
            "analytics; it is not a live SaaS product with production users."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_03_unsupported_ai_llm",
        "claim": (
            "Every feature is powered by GPT-4 in real time, including auto-apply "
            "and email drafting."
        ),
        "evidence": (
            "README denies auto-apply, Gmail, external AI on every request; "
            "CLAUDE.md mocked-first note"
        ),
        "channel": "general",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["ai_automation_overclaim", "integration_overclaim"],
        "expected_rewrite": (
            "Most workflows are rule-based and manual. Some modules have optional mocked-first "
            "LLM paths with rule-based fallback; the app does not auto-apply or send email."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_04_unsupported_revenue",
        "claim": "Generated £50k ARR from enterprise subscriptions in the first quarter.",
        "evidence": "README — no billing, subscriptions, or revenue claims",
        "channel": "general",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["commercial_overclaim"],
        "expected_rewrite": (
            "Personal portfolio project with no commercial revenue, subscriptions, "
            "or paying customers."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_05_unsupported_deployment",
        "claim": "Try the live demo at our production URL — deployed on AWS with 99.9% uptime.",
        "evidence": 'README "Live Demo Status" — deployment not verified',
        "channel": "general",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["forbidden_production_claim", "unverified_deployment_url"],
        "expected_rewrite": (
            "Local Django project for portfolio review; no verified public deployment "
            "URL is claimed."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_06_mixed_safe_unsafe",
        "claim": (
            "Django analytics app with SQLite and 1977 passing tests, currently used by "
            "500 companies worldwide."
        ),
        "evidence": "Phase 4A test log excerpt: Ran 1977 tests ... OK (2026-07-08)",
        "channel": "general",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["commercial_overclaim", "forbidden_production_claim"],
        "expected_rewrite": (
            "Django analytics portfolio app using SQLite, with 1977 passing tests verified locally "
            "on 2026-07-08; single-user portfolio scope, not used by external companies."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_07_unknown_evidence",
        "claim": "CI is green on every push and the test suite has exactly 3000 tests.",
        "evidence": (
            ".github/workflows/django-ci.yml referenced only "
            "(workflow definition, no run result)"
        ),
        "channel": "general",
        "expected_verdict": "needs_evidence",
        "expected_risk": "medium",
        "expected_warnings": ["unverified_test_count", "unverified_ci_status"],
        "expected_rewrite": (
            "CI workflow is defined in the repository; latest run status and exact test count "
            "should be cited from a dated test log or verified Actions run — "
            "otherwise mark as [UNKNOWN]."
        ),
        "require_unknowns": True,
    },
    {
        "name": "case_08_cv_safe_wording",
        "claim": "Shipped enterprise AI platform replacing recruiters with autonomous agents.",
        "evidence": "docs/evidence/phase4a_claim_safety_review.md CV-safe examples",
        "channel": "cv",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["ai_automation_overclaim", "commercial_overclaim"],
        "expected_rewrite": (
            "Built a Django job-search analytics portfolio with rule-based decision support, "
            "documented sprint evidence, and a broad local test suite; manual workflows only."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_09_readme_safe_wording",
        "claim": (
            "Optional Claude semantic path for CV Tailoring Advisor when configured; falls back to "
            "rule-based logic. No external AI on every request."
        ),
        "evidence": 'README "Technical Decisions" §1; Sprint 34 evidence doc path',
        "channel": "github_readme",
        "expected_verdict": "safe",
        "expected_risk": "low",
        "expected_warnings": [],
        "expected_rewrite": (
            "Optional mocked-first Claude path for CV Tailoring Advisor when configured, with "
            "rule-based fallback; external AI is not claimed on every request."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_10_linkedin_safe_wording",
        "claim": "Just launched my AI startup — sign up for our freemium plan!",
        "evidence": "Phase 4A LinkedIn-safe wording section",
        "channel": "linkedin",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["commercial_overclaim", "forbidden_production_claim"],
        "expected_rewrite": (
            "CareerFunnel Tracker is my Django portfolio project for job-search analytics: "
            "funnel metrics, data-quality signals, and evidence docs on GitHub. Manual workflows "
            "only — not a commercial SaaS launch."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_11_interview_answer",
        "claim": "We integrated Gmail and the system automatically replies to recruiters for me.",
        "evidence": (
            "README — Gmail/OAuth not implemented; "
            "recruiter workflow is manual import only"
        ),
        "channel": "interview",
        "expected_verdict": "unsafe",
        "expected_risk": "high",
        "expected_warnings": ["integration_overclaim", "ai_automation_overclaim"],
        "expected_rewrite": (
            "Recruiter email workflow is manual import and rule-based advisory only. There is no "
            "Gmail integration, OAuth, or automatic sending."
        ),
        "require_unknowns": False,
    },
    {
        "name": "case_12_job_application_answer",
        "claim": (
            "In CareerFunnel I designed service-layer analytics with metric governance "
            "and verified 1977 local tests; I run it locally and do not claim production "
            "deployment."
        ),
        "evidence": "Phase 4A test log (1977, 2026-07-08); README metric governance section",
        "channel": "job_application",
        "expected_verdict": "safe",
        "expected_risk": "low",
        "expected_warnings": [],
        "expected_rewrite": (
            "In CareerFunnel Tracker I implemented Django service-layer analytics with metric "
            "definitions, data-quality propagation, and sprint evidence; 1977 tests passed locally "
            "on 2026-07-08. I demonstrate it locally and do not claim a verified production "
            "deployment."
        ),
        "require_unknowns": False,
    },
]


class ClaimSafetyReviewerGoldenTests(SimpleTestCase):
    def test_required_response_fields_present(self):
        response = review_claim_safety(
            "Django portfolio analytics project.",
            evidence_context="README",
        )
        for field_name in REQUIRED_RESPONSE_FIELDS:
            self.assertIn(field_name, response)

    def test_golden_cases(self):
        for case in GOLDEN_CASES:
            with self.subTest(case=case["name"]):
                response = review_claim_safety(
                    case["claim"],
                    evidence_context=case["evidence"],
                    channel=case["channel"],
                )
                valid, errors = validate_claim_safety_response(response)
                self.assertTrue(valid, msg=f"validation errors: {errors}")
                self.assertIn(response["overall_verdict"], VERDICT_VALUES)
                self.assertIn(response["risk_level"], RISK_VALUES)
                self.assertEqual(response["overall_verdict"], case["expected_verdict"])
                self.assertEqual(response["risk_level"], case["expected_risk"])
                for warning in case["expected_warnings"]:
                    self.assertIn(warning, response["warnings"])
                self.assertEqual(
                    _normalize_text(response["safe_rewrite"]),
                    _normalize_text(case["expected_rewrite"]),
                )
                if case["require_unknowns"]:
                    self.assertTrue(response["unknowns"])

    def test_empty_input_returns_unknown(self):
        response = review_claim_safety("   ", evidence_context=None)
        self.assertEqual(response["overall_verdict"], "unknown")
        self.assertEqual(response["risk_level"], "unknown")
        self.assertIn("empty_claim", response["warnings"])


class ClaimSafetyReviewerValidatorTests(SimpleTestCase):
    def test_validator_accepts_valid_response(self):
        response = review_claim_safety(
            "Built a Django portfolio analytics app with funnel metrics.",
            evidence_context="README What The Platform Does",
        )
        valid, errors = validate_claim_safety_response(response)
        self.assertTrue(valid)
        self.assertEqual(errors, [])

    def test_validator_rejects_invalid_verdict(self):
        response = review_claim_safety(
            "Django portfolio analytics.",
            evidence_context="README",
        )
        response["overall_verdict"] = "definitely_safe"
        valid, errors = validate_claim_safety_response(response)
        self.assertFalse(valid)
        self.assertIn("invalid_overall_verdict", errors)

    def test_validator_rejects_invalid_risk(self):
        response = review_claim_safety(
            "Django portfolio analytics.",
            evidence_context="README",
        )
        response["risk_level"] = "critical"
        valid, errors = validate_claim_safety_response(response)
        self.assertFalse(valid)
        self.assertIn("invalid_risk_level", errors)

    def test_validator_rejects_missing_required_fields(self):
        valid, errors = validate_claim_safety_response({})
        self.assertFalse(valid)
        self.assertTrue(any(error.startswith("missing_field:") for error in errors))


class ClaimSafetyReviewerBoundaryTests(SimpleTestCase):
    def test_module_has_no_provider_or_network_imports(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        forbidden_imports = (
            "openai",
            "anthropic",
            "google.generativeai",
            "langchain",
            "requests",
            "httpx",
        )
        for forbidden in forbidden_imports:
            self.assertNotIn(f"import {forbidden}", source)
            self.assertNotIn(f"from {forbidden}", source)

    def test_review_claim_safety_does_not_import_provider_modules(self):
        loaded = importlib.import_module("apps.ai_agents.claim_safety_reviewer")
        self.assertFalse(hasattr(loaded, "openai"))
        self.assertFalse(hasattr(loaded, "anthropic"))
