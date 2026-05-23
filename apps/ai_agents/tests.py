import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import FollowUpStatus, WorkType
from apps.applications.models import JobApplication
from apps.job_intelligence import constants as role_fit_constants

from .services import (
    LOCKED_CV,
    analyze_job_posting,
    build_cv_tailoring_advisor,
    build_next_best_actions,
    build_weekly_coach_report,
    generate_followup_message,
    generate_interview_prep,
)


class RoleFitConstantsTests(TestCase):
    def test_canonical_constants_importable_from_job_intelligence(self):
        self.assertTrue(hasattr(role_fit_constants, "TARGET_TITLES"))

    def test_key_constants_are_nonempty_lists(self):
        for name in (
            "TARGET_TITLES",
            "TARGET_TITLES_AE_STRETCH",
            "BAD_TITLE_WORDS",
            "SENIOR_SIGNALS",
            "GOOD_LOCATION_WORDS",
            "GOOD_SKILLS",
            "DEAL_BREAKERS",
            "LEARNING_TARGETS",
        ):
            value = getattr(role_fit_constants, name)
            self.assertIsInstance(value, list, msg=name)
            self.assertGreater(len(value), 0, msg=name)


class AiAgentServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="FinSight Group",
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            work_type=WorkType.HYBRID,
            required_skills="Python SQL Excel reporting dashboards finance",
            job_description="Junior role for 0-2 years experience working on KPI reporting.",
            date_applied=date(2026, 5, 1),
            follow_up_date=timezone.localdate() - timedelta(days=1),
            follow_up_status=FollowUpStatus.DUE,
        )

    def test_job_posting_analyzer_scores_good_role_at_strong_threshold(self):
        analysis = analyze_job_posting(
            company_name="FinSight",
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            job_posting="Python SQL Excel reporting dashboards junior 0-2 years",
        )
        self.assertGreaterEqual(analysis.fit_score, 70)
        self.assertEqual(analysis.recommended_cv, "Aminul_Islam_Data_Analyst_CV")

    def test_analytics_engineer_with_learning_targets_is_not_auto_rejected(self):
        analysis = analyze_job_posting(
            company_name="Test Company",
            job_title="Junior Analytics Engineer",
            location="Hybrid London",
            job_posting=(
                "We need SQL, Python, dbt, Airflow, dashboards and stakeholder reporting. "
                "This is suitable for 1-2 years experience."
            ),
        )

        self.assertGreaterEqual(analysis.fit_score, 60)
        self.assertNotIn("dbt", analysis.deal_breakers)
        self.assertNotIn("airflow", analysis.deal_breakers)
        self.assertTrue(any("Learning-target tools detected" in risk for risk in analysis.risks))
        self.assertTrue(any("AE/DE stretch target" in risk for risk in analysis.risks))

    def test_true_deal_breakers_still_reduce_score(self):
        analysis = analyze_job_posting(
            company_name="Risk Bank",
            job_title="Senior Data Analyst",
            location="London",
            job_posting=(
                "This role requires SC clearance, ACCA, SQL, Python, and 10+ years "
                "of experience."
            ),
        )

        self.assertIn("sc clearance", analysis.deal_breakers)
        self.assertIn("acca", analysis.deal_breakers)
        self.assertLess(analysis.fit_score, 60)
        self.assertTrue(any("Hard requirement or deal-breaker" in risk for risk in analysis.risks))

    def test_next_best_actions_includes_followup(self):
        actions = build_next_best_actions(self.user)
        self.assertTrue(any("Follow up" in action.title for action in actions))

    def test_followup_message_uses_application(self):
        draft = generate_followup_message(self.application)
        self.assertIn(self.application.job_title, draft.subject)
        self.assertIn(self.application.company_name, draft.body)

    def test_interview_prep_generator_returns_questions(self):
        prep = generate_interview_prep(self.application)
        self.assertGreater(len(prep.likely_questions), 0)
        self.assertGreater(len(prep.projects_to_use), 0)

    def test_weekly_coach_report_builds(self):
        report = build_weekly_coach_report(self.user)
        self.assertTrue(report.headline)
        self.assertGreater(len(report.next_week_plan), 0)


class AiAgentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Test Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
        )

    def test_agent_dashboard_requires_login(self):
        response = self.client.get(reverse("ai_agents:agent_dashboard"))
        self.assertEqual(response.status_code, 302)

    def test_agent_dashboard_loads(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:agent_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_job_analyzer_post_loads_result(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("ai_agents:job_posting_analyzer"),
            {
                "company_name": "Test Co",
                "job_title": "Junior Data Analyst",
                "location": "London",
                "job_posting": "Python SQL Excel reporting junior dashboard",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fit Score")
        self.assertContains(response, "Rule-Based vs AI Score Check")
        self.assertContains(response, "Fallback active")
        self.assertContains(response, "Manual review is required")
        self.assertContains(response, "Advisory Only | Mocked-First")
        self.assertContains(response, "Yes - advisory only")
        self.assertNotContains(response, "┬À")
        self.assertNotContains(response, "ÔÇö")
        from pathlib import Path

        template_path = (
            Path(__file__).resolve().parents[2]
            / "templates"
            / "ai_agents"
            / "job_posting_analyzer.html"
        )
        template_source = template_path.read_text(encoding="utf-8")
        score_check_start = template_source.index('id="rule-based-vs-ai-score-check"')
        score_check_end = template_source.index('id="cv-tailoring-advisor"')
        score_check_section = template_source[score_check_start:score_check_end]
        self.assertIn(
            "Score delta: {{ ai_score_comparison.score_delta }} -",
            score_check_section,
        )
        self.assertNotIn("\u2014", score_check_section)
        self.assertNotIn("\u00b7", score_check_section)
        self.assertContains(response, "AI scoring is advisory only")
        self.assertContains(response, "No application is submitted automatically")
        page_text = response.content.decode()
        self.assertIn("No Gmail, Calendar, scraping, recruiter automation", page_text)
        self.assertIn("auto-apply is used", page_text)
        self.assertContains(response, "CV Tailoring Advisor")
        self.assertContains(response, LOCKED_CV)
        self.assertContains(response, "advisory only")
        self.assertContains(response, "Review and approve")

    def test_followup_writer_post_loads_draft(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("ai_agents:followup_writer"),
            {"application": self.application.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Generated Draft")

    def test_interview_prep_generator_post_loads_pack(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("ai_agents:interview_prep_generator"),
            {"application": self.application.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile Angle")

    def test_application_agent_pack_loads(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )
        self.assertEqual(response.status_code, 200)

    def test_application_agent_pack_shows_cv_tailoring_advisor(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CV Tailoring Advisor")
        self.assertContains(response, LOCKED_CV)
        self.assertContains(response, "Advisory Only")
        self.assertContains(response, "Review and approve")
        self.assertContains(response, "No final CV is generated")

    def test_application_detail_links_to_agent_pack(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            reverse("applications:application_detail", kwargs={"pk": self.application.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Open AI Pack / CV Tailoring Advisor")
        self.assertContains(
            response,
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk}),
        )


class AdvancedAiAgentFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="advanced", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Rejected Co",
            job_title="Senior Analytics Engineer",
            required_skills="dbt Snowflake AWS SQL",
            job_description="Senior role requiring 5+ years and dbt Snowflake AWS.",
            cv_version="AE_CV_v1",
            source="linkedin",
            date_applied=date(2026, 5, 1),
            status="auto_rejected",
        )

    def test_cv_gap_analyzer_service(self):
        from .services import analyze_cv_gap

        analysis = analyze_cv_gap(
            job_description="Python SQL Excel dashboard reporting dbt Snowflake",
            cv_evidence="Python Excel dashboard reporting Django projects",
        )
        self.assertGreaterEqual(analysis.score, 40)
        self.assertIn("dbt", analysis.missing_skills)

    def test_cover_letter_quality_service(self):
        from .services import check_cover_letter_quality

        result = check_cover_letter_quality(
            company_name="Test Co",
            job_title="Data Analyst",
            job_description="Reporting dashboard KPI analysis",
            cover_letter=(
                "Dear Test Co, I am applying for the Data Analyst role. "
                "My BakeOps project shows KPI reporting and dashboard analysis."
            ),
        )
        self.assertGreaterEqual(result.score, 50)

    def test_rejection_pattern_report_builds(self):
        from .services import analyze_rejection_patterns

        report = analyze_rejection_patterns(self.user)
        self.assertEqual(report.total_rejections, 1)
        self.assertTrue(report.recommendations)

    def test_cv_ab_testing_rows_build(self):
        from .services import build_cv_ab_testing_rows

        rows = build_cv_ab_testing_rows(self.user)
        self.assertEqual(rows[0].cv_version, "AE_CV_v1")

    def test_smart_notifications_build(self):
        from .services import build_smart_notifications

        notifications = build_smart_notifications(self.user)
        self.assertTrue(
            any(
                "daily log" in n.title.lower() or "missing" in n.title.lower()
                for n in notifications
            )
        )


class AdvancedAiAgentViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="advancedview", password="StrongPass12345")
        JobApplication.objects.create(
            user=self.user,
            company_name="Test Co",
            job_title="Data Analyst",
            cv_version="DA_CV_v1",
            date_applied=date(2026, 5, 1),
        )

    def test_cv_gap_analyzer_view(self):
        self.client.login(username="advancedview", password="StrongPass12345")
        response = self.client.post(
            reverse("ai_agents:cv_gap_analyzer"),
            {
                "job_description": "Python SQL Excel dashboard reporting",
                "cv_evidence": "Python Excel dashboard reporting",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CV Match Score")

    def test_cover_letter_quality_checker_view(self):
        self.client.login(username="advancedview", password="StrongPass12345")
        response = self.client.post(
            reverse("ai_agents:cover_letter_quality_checker"),
            {
                "company_name": "Test Co",
                "job_title": "Data Analyst",
                "job_description": "KPI dashboard reporting",
                "cover_letter": (
                    "Dear Test Co, I am applying for the Data Analyst role. "
                    "BakeOps shows KPI dashboard reporting."
                ),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quality Score")

    def test_rejection_pattern_view_loads(self):
        self.client.login(username="advancedview", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:rejection_pattern_analyzer"))
        self.assertEqual(response.status_code, 200)

    def test_cv_ab_testing_view_loads(self):
        self.client.login(username="advancedview", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:cv_ab_testing"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CV Version Performance")

    def test_smart_notifications_view_loads(self):
        self.client.login(username="advancedview", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:smart_notifications"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Current Notifications")


class CVTailoringAdvisorLogicTests(TestCase):
    def _result_text(self, result) -> str:
        return " ".join(
            [
                result.recommended_cv,
                result.cv_angle,
                result.role_family,
                " ".join(result.strongest_experience),
                " ".join(result.strongest_projects),
                " ".join(result.risks),
                " ".join(result.deal_breakers),
                " ".join(result.claim_safety_notes),
                result.approval_reminder,
            ]
        ).lower()

    def test_finance_fintech_role_returns_locked_cv_finance_angle_and_projects(self):
        result = build_cv_tailoring_advisor(
            company_name="FinSight",
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            job_description=(
                "Python SQL Excel finance reporting banking risk reconciliation KPI "
                "junior 0-2 years"
            ),
            cv_evidence="Python Excel finance reporting reconciliation Django",
        )
        self.assertEqual(result.recommended_cv, LOCKED_CV)
        self.assertIn("Finance", result.cv_angle)
        self.assertEqual(result.role_family, "Finance / FinTech Analytics")
        self.assertTrue(
            any(
                project in result.strongest_projects
                for project in ("TradeIntel 360", "RiskWise Planner", "MarketVista Dashboard")
            )
        )
        self.assertTrue(
            any(
                "reconciliation" in item.lower()
                for item in result.strongest_experience
            )
        )

    def test_bi_reporting_role_returns_locked_cv_reporting_angle_and_projects(self):
        result = build_cv_tailoring_advisor(
            job_title="BI Analyst",
            location="London",
            job_description=(
                "Power BI Tableau dashboard reporting KPI stakeholder insights "
                "business intelligence junior"
            ),
            cv_evidence="Python Excel dashboard reporting stakeholder",
        )
        self.assertEqual(result.recommended_cv, LOCKED_CV)
        self.assertIn("BI", result.cv_angle)
        self.assertEqual(result.role_family, "BI / Reporting Analytics")
        self.assertIn("BakeOps Intelligence", result.strongest_projects)
        self.assertIn("MarketVista Dashboard", result.strongest_projects)

    def test_etl_api_pipeline_role_returns_ae_stretch_angle_and_projects(self):
        result = build_cv_tailoring_advisor(
            job_title="Junior Analytics Engineer",
            location="Remote UK",
            job_description=(
                "ETL API pipeline integration SQL Python dashboards stakeholder "
                "reporting 1-2 years"
            ),
            cv_evidence="Python SQL API Django reporting",
        )
        self.assertEqual(result.recommended_cv, LOCKED_CV)
        self.assertIn("Analytics Engineering", result.cv_angle)
        self.assertEqual(result.role_family, "Analytics Engineering / Data Product Stretch")
        self.assertIn("DataBridge Market API", result.strongest_projects)

    def test_senior_clearance_role_surfaces_deal_breakers_and_review_risk(self):
        result = build_cv_tailoring_advisor(
            job_title="Senior Data Analyst",
            location="London",
            job_description=(
                "SC clearance required ACCA SQL Python 10+ years senior data analyst "
                "reporting"
            ),
        )
        self.assertEqual(result.recommended_cv, LOCKED_CV)
        self.assertIn("sc clearance", result.deal_breakers)
        self.assertTrue(result.deal_breakers)
        self.assertEqual(result.role_family, "Review Carefully")
        self.assertIn("Review-first", result.cv_angle)
        self.assertTrue(
            any(
                "seniority" in risk.lower() or "deal-breaker" in risk.lower()
                for risk in result.risks
            )
        )

    def test_missing_dbt_snowflake_airflow_treated_as_gaps_not_invented_experience(self):
        result = build_cv_tailoring_advisor(
            job_title="Data Analyst",
            job_description="Python SQL dbt Snowflake Airflow required for reporting",
            cv_evidence="Python Excel dashboard reporting Django",
        )
        gap_text = " ".join(
            result.missing_skills + result.partial_matches + result.risks
        ).lower()
        self.assertTrue(
            any(tool in gap_text for tool in ("dbt", "snowflake", "airflow"))
        )
        experience_text = " ".join(result.strongest_experience).lower()
        self.assertNotIn("dbt production expert", experience_text)
        self.assertNotIn("snowflake architect", experience_text)

    def test_advisor_output_contains_manual_approval_safety_language(self):
        result = build_cv_tailoring_advisor(
            job_title="Junior Data Analyst",
            job_description="Python SQL Excel reporting junior London",
        )
        self.assertIn("advisory only", " ".join(result.claim_safety_notes).lower())
        self.assertIn("manually approve", " ".join(result.claim_safety_notes).lower())
        self.assertIn("review and approve", result.approval_reminder.lower())

    def test_advisor_does_not_invent_alternative_cv_filenames(self):
        result = build_cv_tailoring_advisor(
            job_title="Finance Data Analyst",
            job_description="finance risk banking reporting bi etl api",
        )
        blob = self._result_text(result)
        for forbidden in (
            "finance_da_cv_v1",
            "bi_reporting_cv_v1",
            "ae_data_product_cv_v1",
            "da_cv_v2",
        ):
            self.assertNotIn(forbidden, blob)
        self.assertEqual(result.recommended_cv, LOCKED_CV)

    def test_advisor_does_not_claim_forbidden_automation_features(self):
        result = build_cv_tailoring_advisor(
            job_title="Reporting Analyst",
            job_description="reporting dashboard KPI",
        )
        safety_text = " ".join(result.claim_safety_notes).lower()
        self.assertIn("no final cv is generated", safety_text)
        self.assertIn("no gmail", safety_text)
        self.assertIn("no cover letter is finalized", safety_text)
        self.assertIn("no application is submitted", safety_text)
        self.assertIn("external ai", safety_text)
        self.assertIn("recruiter automation", safety_text)
        self.assertNotIn("gmail integration is active", safety_text)


class AIFitScoringContractTests(TestCase):
    def _valid_payload(self, **overrides):
        payload = {
            "ai_fit_score": 72,
            "ai_fit_label": "Good selective fit",
            "confidence": "medium",
            "evidence_matches": ["Python", "SQL"],
            "gaps": ["dbt"],
            "deal_breakers": [],
            "reasoning_summary": "Strong overlap with portfolio evidence.",
            "recommended_cv_angle": "BI reporting and dashboard angle.",
            "recommended_projects": ["BakeOps Intelligence"],
            "manual_review_required": False,
            "claim_safety_notes": ["Treat as advisory."],
        }
        payload.update(overrides)
        return payload

    def test_valid_mocked_payload_parses_into_ai_fit_scoring_result(self):
        from .services import build_ai_fit_scoring_result_from_mock

        result = build_ai_fit_scoring_result_from_mock(self._valid_payload())
        self.assertEqual(result.ai_fit_score, 72)
        self.assertEqual(result.ai_fit_label, "Good selective fit")
        self.assertEqual(result.confidence, "medium")

    def test_ai_fit_score_must_be_between_zero_and_hundred(self):
        from .services import parse_ai_fit_scoring_payload

        with self.assertRaises(ValueError):
            parse_ai_fit_scoring_payload(self._valid_payload(ai_fit_score=150))

    def test_confidence_must_be_low_medium_or_high(self):
        from .services import parse_ai_fit_scoring_payload

        with self.assertRaises(ValueError):
            parse_ai_fit_scoring_payload(self._valid_payload(confidence="very-high"))

    def test_list_fields_must_be_lists_of_strings(self):
        from .services import parse_ai_fit_scoring_payload

        with self.assertRaises(ValueError):
            parse_ai_fit_scoring_payload(
                self._valid_payload(evidence_matches=["Python", 99])
            )

    def test_manual_review_required_remains_true_when_payload_false(self):
        from .services import parse_ai_fit_scoring_payload

        result = parse_ai_fit_scoring_payload(
            self._valid_payload(manual_review_required=False)
        )
        self.assertTrue(result.manual_review_required)

    def test_claim_safety_notes_include_advisory_and_boundary_language(self):
        from .services import parse_ai_fit_scoring_payload

        result = parse_ai_fit_scoring_payload(self._valid_payload())
        notes = " ".join(result.claim_safety_notes).lower()
        self.assertIn("advisory only", notes)
        self.assertIn("manual review", notes)
        self.assertIn("no application is submitted", notes)
        self.assertIn("openai", notes)
        self.assertIn("auto-apply", notes)

    def test_score_comparison_flags_disagreement_above_threshold(self):
        from .services import (
            AI_SCORE_DISAGREEMENT_THRESHOLD,
            build_ai_fit_scoring_result_from_mock,
            compare_rule_based_and_ai_scores,
        )

        ai_result = build_ai_fit_scoring_result_from_mock(
            self._valid_payload(
                ai_fit_score=50 + AI_SCORE_DISAGREEMENT_THRESHOLD + 1
            )
        )
        comparison = compare_rule_based_and_ai_scores(50, ai_result)
        self.assertTrue(comparison.disagreement_flag)
        self.assertEqual(
            comparison.score_delta,
            AI_SCORE_DISAGREEMENT_THRESHOLD + 1,
        )
        self.assertIn("differ materially", comparison.disagreement_summary.lower())

    def test_score_comparison_no_disagreement_within_threshold(self):
        from .services import (
            build_ai_fit_scoring_result_from_mock,
            compare_rule_based_and_ai_scores,
        )

        ai_result = build_ai_fit_scoring_result_from_mock(
            self._valid_payload(ai_fit_score=60)
        )
        comparison = compare_rule_based_and_ai_scores(50, ai_result)
        self.assertFalse(comparison.disagreement_flag)
        self.assertEqual(comparison.score_delta, 10)
        self.assertIn("broadly aligned", comparison.disagreement_summary.lower())

    def test_invalid_rule_based_score_raises_value_error(self):
        from .services import (
            build_ai_fit_scoring_result_from_mock,
            compare_rule_based_and_ai_scores,
        )

        ai_result = build_ai_fit_scoring_result_from_mock(self._valid_payload())
        with self.assertRaises(ValueError):
            compare_rule_based_and_ai_scores(150, ai_result)

    def test_comparison_always_requires_manual_review(self):
        from .services import (
            build_ai_fit_scoring_result_from_mock,
            compare_rule_based_and_ai_scores,
        )

        ai_result = build_ai_fit_scoring_result_from_mock(self._valid_payload())
        comparison = compare_rule_based_and_ai_scores(70, ai_result)
        self.assertTrue(comparison.manual_review_required)

    def test_services_module_has_no_provider_client_imports(self):
        from pathlib import Path

        source = Path(__file__).resolve().parent.joinpath("services.py").read_text(
            encoding="utf-8"
        ).lower()
        forbidden = (
            "import openai",
            "from openai",
            "import anthropic",
            "import httpx",
            "import requests",
            "from urllib",
        )
        for pattern in forbidden:
            self.assertNotIn(pattern, source)


class OpenAIFitScoringWrapperTests(TestCase):
    def _valid_provider_payload(self, **overrides):
        payload = {
            "ai_fit_score": 68,
            "ai_fit_label": "Mocked provider fit",
            "confidence": "medium",
            "evidence_matches": ["Python"],
            "gaps": [],
            "deal_breakers": [],
            "reasoning_summary": "Mocked provider reasoning.",
            "recommended_cv_angle": "General analytics angle.",
            "recommended_projects": ["CareerFunnel Tracker"],
            "claim_safety_notes": ["Provider mock only."],
        }
        payload.update(overrides)
        return payload

    def _job_fields(self):
        return {
            "company_name": "Test Co",
            "job_title": "Junior Data Analyst",
            "location": "London",
            "job_description": "Python SQL Excel reporting junior dashboard London",
        }

    def test_prompt_builder_returns_structured_dict(self):
        from .services import analyze_job_posting, build_openai_fit_scoring_prompt

        fields = self._job_fields()
        rule_based = analyze_job_posting(
            company_name=fields["company_name"],
            job_title=fields["job_title"],
            location=fields["location"],
            job_posting=fields["job_description"],
        )
        prompt = build_openai_fit_scoring_prompt(
            rule_based_analysis=rule_based,
            **fields,
        )
        self.assertEqual(prompt["company_name"], "Test Co")
        self.assertEqual(prompt["rule_based_fit_score"], rule_based.fit_score)
        self.assertEqual(prompt["rule_based_recommendation"], rule_based.recommendation)
        self.assertIn("required_output_schema", prompt)
        self.assertIn("fields", prompt["required_output_schema"])
        self.assertTrue(prompt["safety_rules"])

    def test_wrapper_returns_fallback_when_provider_missing(self):
        from .services import build_openai_fit_scoring_with_fallback

        result = build_openai_fit_scoring_with_fallback(**self._job_fields())
        self.assertTrue(result.used_fallback)
        self.assertIsNone(result.ai_result)
        self.assertIn("Provider callable is missing", result.fallback_reason)

    def test_wrapper_returns_parsed_result_for_valid_mock_provider(self):
        from .services import build_openai_fit_scoring_with_fallback

        def mock_provider(prompt):
            self.assertIn("rule_based_fit_score", prompt)
            return self._valid_provider_payload()

        result = build_openai_fit_scoring_with_fallback(
            **self._job_fields(),
            provider_callable=mock_provider,
        )
        self.assertFalse(result.used_fallback)
        self.assertIsNotNone(result.ai_result)
        self.assertEqual(result.ai_result.ai_fit_score, 68)

    def test_wrapper_catches_provider_exception(self):
        from .services import build_openai_fit_scoring_with_fallback

        def failing_provider(prompt):
            raise RuntimeError("mock provider failure")

        result = build_openai_fit_scoring_with_fallback(
            **self._job_fields(),
            provider_callable=failing_provider,
        )
        self.assertTrue(result.used_fallback)
        self.assertIn("Provider callable failed", result.fallback_reason)

    def test_wrapper_catches_invalid_provider_payload(self):
        from .services import build_openai_fit_scoring_with_fallback

        def bad_provider(prompt):
            return self._valid_provider_payload(ai_fit_score=200)

        result = build_openai_fit_scoring_with_fallback(
            **self._job_fields(),
            provider_callable=bad_provider,
        )
        self.assertTrue(result.used_fallback)
        self.assertIn("validation failed", result.fallback_reason.lower())

    def test_wrapper_always_preserves_manual_review_required(self):
        from .services import build_openai_fit_scoring_with_fallback

        missing = build_openai_fit_scoring_with_fallback(**self._job_fields())
        self.assertTrue(missing.manual_review_required)

        def mock_provider(prompt):
            return self._valid_provider_payload()

        parsed = build_openai_fit_scoring_with_fallback(
            **self._job_fields(),
            provider_callable=mock_provider,
        )
        self.assertTrue(parsed.manual_review_required)

    def test_wrapper_claim_safety_notes_include_mocked_first_boundaries(self):
        from .services import build_openai_fit_scoring_with_fallback

        result = build_openai_fit_scoring_with_fallback(**self._job_fields())
        notes = " ".join(result.claim_safety_notes).lower()
        self.assertIn("mocked-first", notes)
        self.assertIn("no real openai call", notes)
        self.assertIn("no api key", notes)
        self.assertIn("manual review", notes)
        self.assertIn("auto-apply", notes)

    def test_comparison_returns_none_when_fallback_has_no_ai_result(self):
        from .services import (
            analyze_job_posting,
            build_openai_fit_scoring_with_fallback,
            compare_openai_wrapper_result_with_rule_based,
        )

        fields = self._job_fields()
        wrapper = build_openai_fit_scoring_with_fallback(**fields)
        rule_based = analyze_job_posting(
            company_name=fields["company_name"],
            job_title=fields["job_title"],
            location=fields["location"],
            job_posting=fields["job_description"],
        )
        comparison = compare_openai_wrapper_result_with_rule_based(
            rule_based.fit_score,
            wrapper,
        )
        self.assertIsNone(comparison)

    def test_comparison_returns_fit_comparison_when_ai_result_exists(self):
        from .services import (
            analyze_job_posting,
            build_openai_fit_scoring_with_fallback,
            compare_openai_wrapper_result_with_rule_based,
        )

        fields = self._job_fields()

        def mock_provider(prompt):
            return self._valid_provider_payload(ai_fit_score=80)

        wrapper = build_openai_fit_scoring_with_fallback(
            **fields,
            provider_callable=mock_provider,
        )
        rule_based = analyze_job_posting(
            company_name=fields["company_name"],
            job_title=fields["job_title"],
            location=fields["location"],
            job_posting=fields["job_description"],
        )
        comparison = compare_openai_wrapper_result_with_rule_based(
            rule_based.fit_score,
            wrapper,
        )
        self.assertIsNotNone(comparison)
        self.assertEqual(comparison.ai_fit_score, 80)
        self.assertEqual(comparison.rule_based_score, rule_based.fit_score)

    def test_services_module_has_no_provider_network_imports(self):
        from pathlib import Path

        source = Path(__file__).resolve().parent.joinpath("services.py").read_text(
            encoding="utf-8"
        ).lower()
        forbidden = (
            "import openai",
            "from openai",
            "import anthropic",
            "import httpx",
            "import requests",
            "from urllib",
            "os.environ",
            "django.conf.settings",
            "from django.conf import settings",
        )
        for pattern in forbidden:
            self.assertNotIn(pattern, source)


class TestClaudeProvider(TestCase):
    def _valid_ai_payload_json(self) -> str:
        return json.dumps({
            "ai_fit_score": 72,
            "ai_fit_label": "Moderate Match",
            "confidence": "medium",
            "evidence_matches": ["Python", "SQL"],
            "gaps": ["Tableau"],
            "deal_breakers": [],
            "reasoning_summary": "Good skill overlap for a junior role.",
            "recommended_cv_angle": "General Data Analyst angle.",
            "recommended_projects": ["BakeOps Intelligence"],
            "claim_safety_notes": ["Advisory only; manual review required."],
        })

    def _make_mock_response(self, text: str) -> MagicMock:
        block = MagicMock()
        block.type = "text"
        block.text = text
        response = MagicMock()
        response.content = [block]
        return response

    def _sample_prompt(self) -> dict:
        return {
            "company_name": "Test Co",
            "job_title": "Junior Data Analyst",
            "location": "London",
            "job_description": "Python SQL reporting junior",
            "rule_based_fit_score": 65,
            "rule_based_recommendation": "Apply selectively",
            "matched_skills": ["python", "sql"],
            "risks": [],
            "deal_breakers": [],
            "required_output_schema": {
                "fields": [
                    "ai_fit_score", "ai_fit_label", "confidence",
                    "evidence_matches", "gaps", "deal_breakers",
                    "reasoning_summary", "recommended_cv_angle",
                    "recommended_projects", "claim_safety_notes",
                ],
                "score_range": {"min": 0, "max": 100},
                "confidence_values": ["high", "low", "medium"],
            },
        }

    def test_make_claude_provider_returns_callable(self):
        from .claude_provider import make_claude_provider

        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic"):
            provider = make_claude_provider("test-key")
        self.assertTrue(callable(provider))

    def test_callable_returns_valid_dict_for_well_formed_response(self):
        from .claude_provider import make_claude_provider

        mock_response = self._make_mock_response(self._valid_ai_payload_json())
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_provider("test-key")
            result = provider(self._sample_prompt())
        self.assertIsInstance(result, dict)
        self.assertEqual(result["ai_fit_score"], 72)
        self.assertEqual(result["confidence"], "medium")
        self.assertIn("Python", result["evidence_matches"])

    def test_callable_raises_value_error_when_response_content_empty(self):
        from .claude_provider import make_claude_provider

        empty_response = MagicMock()
        empty_response.content = []
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = empty_response
            provider = make_claude_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_prompt())
        self.assertIn("empty", str(ctx.exception).lower())

    def test_callable_raises_value_error_when_json_is_malformed(self):
        from .claude_provider import make_claude_provider

        mock_response = self._make_mock_response("not valid json {{{")
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_prompt())
        self.assertIn("not valid json", str(ctx.exception).lower())

    def test_callable_raises_value_error_when_result_is_not_dict(self):
        from .claude_provider import make_claude_provider

        mock_response = self._make_mock_response('["a", "b", "c"]')
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_prompt())
        self.assertIn("json object", str(ctx.exception).lower())

    def test_wrapper_uses_fallback_when_provider_callable_is_none(self):
        from .services import build_openai_fit_scoring_with_fallback

        result = build_openai_fit_scoring_with_fallback(
            company_name="Test Co",
            job_title="Junior Data Analyst",
            location="London",
            job_description="Python SQL reporting junior",
            provider_callable=None,
        )
        self.assertTrue(result.used_fallback)
        self.assertIsNone(result.ai_result)

    def test_wrapper_uses_fallback_when_provider_raises_value_error(self):
        from .services import build_openai_fit_scoring_with_fallback

        def bad_provider(prompt):
            raise ValueError("Simulated malformed Claude response")

        result = build_openai_fit_scoring_with_fallback(
            company_name="Test Co",
            job_title="Junior Data Analyst",
            location="London",
            job_description="Python SQL reporting junior",
            provider_callable=bad_provider,
        )
        self.assertTrue(result.used_fallback)
        self.assertIn("validation failed", result.fallback_reason.lower())