import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import FollowUpStatus, WorkType
from apps.applications.models import JobApplication
from apps.job_intelligence import constants as role_fit_constants
from apps.weekly_review.choices import FunnelDiagnosis, WeeklyMood
from apps.weekly_review.models import WeeklyReview

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


class AiAgentWeeklyCoachPolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Coach Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
        )

    def test_weekly_coach_page_contains_advisory_trust_copy(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:weekly_coach"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "advisory only")
        self.assertContains(response, "rule-based")
        self.assertContains(response, "does not save weekly reviews")
        self.assertContains(response, "manually saved Weekly Review")

    def test_weekly_coach_links_to_weekly_review_dashboard_and_metrics(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:weekly_coach"))
        self.assertContains(response, reverse("weekly_review:weekly_review_list"))
        self.assertContains(response, reverse("weekly_review:weekly_review_create"))
        self.assertContains(response, reverse("dashboard:overview"))
        self.assertContains(response, reverse("metrics:funnel_metrics"))

    def test_weekly_coach_shows_latest_weekly_review_context(self):
        review = WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 17),
            target_applications=12,
            actual_applications=9,
            diagnosis=FunnelDiagnosis.CV_TARGETING,
            mood=WeeklyMood.MIXED,
        )
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:weekly_coach"))
        self.assertContains(response, "Latest Weekly Review")
        self.assertContains(response, "May 2026")
        self.assertContains(response, "12")
        self.assertContains(response, review.get_diagnosis_display())
        self.assertContains(response, review.get_absolute_url())

    def test_weekly_coach_handles_no_weekly_review(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:weekly_coach"))
        self.assertContains(response, "No Weekly Review saved yet")
        self.assertContains(response, reverse("weekly_review:weekly_review_create"))

    def test_weekly_coach_get_does_not_mutate_weekly_reviews_or_applications(self):
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
        )
        review_count_before = WeeklyReview.objects.filter(user=self.user).count()
        application_count_before = JobApplication.objects.filter(user=self.user).count()
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:weekly_coach"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            WeeklyReview.objects.filter(user=self.user).count(),
            review_count_before,
        )
        self.assertEqual(
            JobApplication.objects.filter(user=self.user).count(),
            application_count_before,
        )

    def test_agent_dashboard_uses_optional_claude_claim_safe_wording(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:agent_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No external AI model or API is called")
        self.assertContains(response, "optional Claude")
        self.assertContains(response, "rule-based")
        self.assertContains(response, "Manual review is required")

    def test_agent_nav_links_to_weekly_review(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("ai_agents:weekly_coach"))
        self.assertContains(response, reverse("weekly_review:weekly_review_list"))
        self.assertContains(response, "Weekly Review")


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


class ApplicationAgentPackCrossLinkTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="packlink", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Pack Co",
            job_title="BI Analyst",
            date_applied=date(2026, 5, 1),
        )
        self.client.login(username="packlink", password="StrongPass12345")

    def test_application_agent_pack_links_to_application_detail(self):
        application_url = reverse(
            "applications:application_detail",
            kwargs={"pk": self.application.pk},
        )
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.assertContains(response, application_url)
        self.assertContains(response, "Application Detail")

    def test_application_agent_pack_links_to_recruiter_import(self):
        import_url = reverse(
            "recruiter_emails:import",
            kwargs={"application_id": self.application.pk},
        )
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.assertContains(response, import_url)
        self.assertContains(response, "Import recruiter email")

    def test_application_agent_pack_links_to_interview_create_with_application(self):
        interview_url = (
            reverse("interviews:interview_create") + f"?application={self.application.pk}"
        )
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.assertContains(response, interview_url)

    def test_application_agent_pack_lists_existing_interview_prep(self):
        from apps.interviews.models import InterviewPrep

        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 15),
        )
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.assertContains(response, "Saved interview prep for this application")
        self.assertContains(response, interview.get_absolute_url())

    def test_application_agent_pack_links_latest_recruiter_email(self):
        from apps.recruiter_emails.models import RecruiterEmail

        recruiter_email = RecruiterEmail.objects.create(
            application=self.application,
            subject="Latest recruiter note",
            body="Following up on your application.",
            date_received=timezone.now(),
        )
        detail_url = reverse(
            "recruiter_emails:detail",
            kwargs={"pk": recruiter_email.pk},
        )
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.assertContains(response, detail_url)
        self.assertContains(response, "Latest recruiter email")

    def test_application_agent_pack_manual_advisory_only_copy(self):
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.assertContains(response, "Application AI Pack is advisory only")
        self.assertContains(response, "no interview prep is created automatically")
        self.assertContains(response, "prepare manually before taking action")

    def test_application_agent_pack_no_gmail_oauth_calendar_claims(self):
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.assertContains(response, "No Gmail, Calendar, OAuth")

    def test_application_agent_pack_does_not_mutate_application_on_get(self):
        from apps.interviews.models import InterviewPrep
        from apps.recruiter_emails.models import RecruiterEmail

        original_status = self.application.status
        RecruiterEmail.objects.create(
            application=self.application,
            subject="Interview",
            body="We would like to invite you to interview.",
            date_received=timezone.now(),
            matched_signals='["interview"]',
        )
        prep_count_before = InterviewPrep.objects.count()

        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )

        self.application.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.application.status, original_status)
        self.assertEqual(InterviewPrep.objects.count(), prep_count_before)
        self.assertTrue(response.context["has_interview_signal"])


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

    def test_provider_callable_returns_valid_dict_from_mock_response(self):
        from .claude_provider import make_claude_provider
        from .services import AI_SCORING_REQUIRED_PAYLOAD_FIELDS

        mock_response = self._make_mock_response(self._valid_ai_payload_json())
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_provider("test-key")
            result = provider(self._sample_prompt())
        self.assertIsInstance(result, dict)
        for field in AI_SCORING_REQUIRED_PAYLOAD_FIELDS:
            self.assertIn(field, result)

    def test_provider_callable_raises_value_error_when_response_content_empty(self):
        from .claude_provider import make_claude_provider

        empty_response = MagicMock()
        empty_response.content = []
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = empty_response
            provider = make_claude_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_prompt())
        self.assertIn("empty", str(ctx.exception).lower())

    def test_provider_callable_raises_value_error_when_json_malformed(self):
        from .claude_provider import make_claude_provider

        mock_response = self._make_mock_response("not valid json {{{")
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_prompt())
        self.assertIn("not valid json", str(ctx.exception).lower())

    def test_provider_callable_raises_value_error_when_parsed_result_is_not_dict(self):
        from .claude_provider import make_claude_provider

        mock_response = self._make_mock_response('["a", "b", "c"]')
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_prompt())
        self.assertIn("json object", str(ctx.exception).lower())

    def test_openai_wrapper_returns_fallback_when_provider_callable_none(self):
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
        self.assertTrue(result.manual_review_required)

    def test_openai_wrapper_returns_fallback_when_provider_callable_raises_value_error(
        self,
    ):
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
        self.assertIsNone(result.ai_result)
        self.assertTrue(result.manual_review_required)


class EvidenceBankTests(TestCase):
    def test_evidence_entries_are_non_empty_and_tiered(self):
        from .evidence_bank import EVIDENCE_ENTRIES, EvidenceTier

        self.assertGreater(len(EVIDENCE_ENTRIES), 0)
        allowed_tiers: set[EvidenceTier] = {"strong", "partial", "gap_learning"}
        for skill_id, entry in EVIDENCE_ENTRIES.items():
            self.assertEqual(entry.skill_id, skill_id)
            self.assertIn(entry.tier, allowed_tiers)
            self.assertTrue(entry.display_name)
            self.assertTrue(entry.evidence_summary)
            if entry.tier == "gap_learning":
                self.assertFalse(entry.claimable)
            else:
                self.assertTrue(entry.claimable)

    def test_project_entries_use_canonical_display_names(self):
        from .evidence_bank import PROJECT_ENTRIES

        expected = {
            "CareerFunnel Tracker",
            "BakeOps Intelligence",
            "MarketVista Dashboard",
            "DataBridge Market API",
            "TradeIntel 360",
            "RiskWise Planner",
        }
        display_names = {entry.display_name for entry in PROJECT_ENTRIES.values()}
        self.assertEqual(display_names, expected)
        for entry in PROJECT_ENTRIES.values():
            self.assertTrue(entry.role_families)
            self.assertTrue(entry.evidence_summary)

    def test_learning_targets_are_gap_learning_not_claimable(self):
        from apps.job_intelligence.constants import LEARNING_TARGETS

        from .evidence_bank import (
            GAP_LEARNING_SKILL_IDS,
            get_evidence_entry,
            is_claimable_skill,
        )

        for target in LEARNING_TARGETS:
            skill_id = target.strip().lower().replace(" ", "_")
            self.assertIn(
                skill_id,
                GAP_LEARNING_SKILL_IDS,
                msg=f"Expected gap registry to include learning target: {target}",
            )
            entry = get_evidence_entry(skill_id)
            self.assertIsNotNone(entry, msg=f"Missing evidence entry for: {target}")
            self.assertEqual(entry.tier, "gap_learning")
            self.assertFalse(entry.claimable)
            self.assertFalse(is_claimable_skill(skill_id))

    def test_filter_claimable_for_matched_strips_gap_tier_skills(self):
        from .evidence_bank import filter_claimable_for_matched

        skill_ids = [
            "python",
            "sql",
            "dbt",
            "snowflake",
            "airflow",
            "spark",
            "kafka",
            "django",
        ]
        claimable = filter_claimable_for_matched(skill_ids)
        self.assertEqual(claimable, ["python", "django"])
        self.assertNotIn("dbt", claimable)
        self.assertNotIn("snowflake", claimable)
        self.assertNotIn("airflow", claimable)
        self.assertNotIn("spark", claimable)
        self.assertNotIn("kafka", claimable)
        self.assertNotIn("sql", claimable)

    def test_validate_project_names_rejects_unknown_projects(self):
        from .evidence_bank import validate_project_names

        names = [
            "BakeOps Intelligence",
            "Unknown Portfolio App",
            "CareerFunnel Tracker",
            "BakeOps Intelligence",
        ]
        validated = validate_project_names(names)
        self.assertEqual(
            validated,
            ["BakeOps Intelligence", "CareerFunnel Tracker"],
        )

    def test_hard_gap_terms_never_promoted_to_strong(self):
        from .evidence_bank import HARD_GAP_SKILL_IDS, get_evidence_entry, is_claimable_skill

        for skill_id in HARD_GAP_SKILL_IDS:
            entry = get_evidence_entry(skill_id)
            self.assertIsNotNone(entry, msg=f"Missing hard-gap entry: {skill_id}")
            self.assertNotEqual(entry.tier, "strong")
            self.assertFalse(is_claimable_skill(skill_id))

    def test_unknown_skill_is_not_claimable(self):
        from .evidence_bank import (
            filter_claimable_for_matched,
            get_evidence_entry,
            is_claimable_skill,
            tier_for_skill,
        )

        self.assertIsNone(get_evidence_entry("terraform"))
        self.assertIsNone(tier_for_skill("terraform"))
        self.assertFalse(is_claimable_skill("terraform"))
        self.assertEqual(
            filter_claimable_for_matched(["python", "terraform", "dbt"]),
            ["python"],
        )

    def test_forbidden_claim_field_detector_flags_cv_body_fields(self):
        from .evidence_bank import contains_forbidden_claim_field

        for field in (
            "full_cv_text",
            "professional_summary",
            "experience_bullets",
            "cover_letter_body",
        ):
            self.assertTrue(
                contains_forbidden_claim_field(field),
                msg=f"Expected forbidden field detection for: {field}",
            )
        self.assertFalse(contains_forbidden_claim_field("semantic_matched_skills"))
        self.assertFalse(contains_forbidden_claim_field(""))


class TestClaudeCvTailoringProvider(TestCase):
    def _valid_cv_tailoring_payload(self, **overrides):
        payload = {
            "semantic_matched_skills": ["python", "django"],
            "semantic_partial_matches": ["sql"],
            "semantic_gaps": ["dbt"],
            "semantic_project_highlights": ["BakeOps Intelligence"],
            "semantic_experience_angles": ["Operational reporting and KPI tracking"],
            "semantic_risks": ["Learning-target tool mentioned in JD."],
            "semantic_cover_letter_themes": [
                "Connect portfolio KPI work to reporting needs."
            ],
            "semantic_interview_points": [
                "Explain one portfolio project from problem to output."
            ],
            "reasoning_summary": "Strong Python overlap; treat dbt as a gap.",
            "claim_safety_notes": ["Semantic output is advisory only."],
            "manual_review_required": True,
        }
        payload.update(overrides)
        return payload

    def _valid_cv_tailoring_payload_json(self) -> str:
        return json.dumps(self._valid_cv_tailoring_payload())

    def _make_mock_response(self, text: str) -> MagicMock:
        block = MagicMock()
        block.type = "text"
        block.text = text
        response = MagicMock()
        response.content = [block]
        return response

    def _sample_cv_tailoring_prompt(self) -> dict:
        return {
            "company_name": "Test Co",
            "job_title": "Junior Data Analyst",
            "location": "London",
            "job_description": "Python SQL reporting junior",
            "cv_evidence": "Python Django reporting",
            "rule_based": {
                "cv_angle": "General Data Analyst",
                "role_family": "Data Analyst",
                "matched_skills": ["python"],
                "partial_matches": ["sql"],
                "missing_skills": ["dbt"],
                "strongest_projects": ["CareerFunnel Tracker"],
                "risks": [],
                "deal_breakers": [],
            },
            "evidence_catalog": {
                "strong_skills": ["python"],
                "partial_skills": ["sql"],
                "gap_learning_skills": ["dbt"],
                "projects": ["CareerFunnel Tracker"],
            },
            "required_output_schema": {
                "fields": [
                    "semantic_matched_skills",
                    "semantic_partial_matches",
                    "semantic_gaps",
                    "semantic_project_highlights",
                    "semantic_experience_angles",
                    "semantic_risks",
                    "semantic_cover_letter_themes",
                    "semantic_interview_points",
                    "reasoning_summary",
                    "claim_safety_notes",
                    "manual_review_required",
                ],
                "forbidden_fields": ["full_cv_text", "recommended_cv"],
            },
            "safety_rules": ["Output is advisory only."],
        }

    def test_make_claude_cv_tailoring_provider_returns_callable(self):
        from .claude_provider import make_claude_cv_tailoring_provider

        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic"):
            provider = make_claude_cv_tailoring_provider("test-key")
        self.assertTrue(callable(provider))

    def test_cv_tailoring_provider_returns_valid_dict_from_mock_response(self):
        from .claude_provider import make_claude_cv_tailoring_provider
        from .services import CV_TAILORING_SEMANTIC_REQUIRED_FIELDS

        mock_response = self._make_mock_response(self._valid_cv_tailoring_payload_json())
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_cv_tailoring_provider("test-key")
            result = provider(self._sample_cv_tailoring_prompt())
        self.assertIsInstance(result, dict)
        for field in CV_TAILORING_SEMANTIC_REQUIRED_FIELDS:
            self.assertIn(field, result)

    def test_cv_tailoring_provider_raises_value_error_when_response_content_empty(self):
        from .claude_provider import make_claude_cv_tailoring_provider

        empty_response = MagicMock()
        empty_response.content = []
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = empty_response
            provider = make_claude_cv_tailoring_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_cv_tailoring_prompt())
        self.assertIn("empty", str(ctx.exception).lower())

    def test_cv_tailoring_provider_raises_value_error_when_json_malformed(self):
        from .claude_provider import make_claude_cv_tailoring_provider

        mock_response = self._make_mock_response("not valid json {{{")
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_cv_tailoring_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_cv_tailoring_prompt())
        self.assertIn("not valid json", str(ctx.exception).lower())

    def test_cv_tailoring_provider_raises_value_error_when_parsed_result_is_not_dict(
        self,
    ):
        from .claude_provider import make_claude_cv_tailoring_provider

        mock_response = self._make_mock_response('["a", "b"]')
        with patch("apps.ai_agents.claude_provider.anthropic.Anthropic") as mock_cls:
            mock_cls.return_value.messages.create.return_value = mock_response
            provider = make_claude_cv_tailoring_provider("test-key")
            with self.assertRaises(ValueError) as ctx:
                provider(self._sample_cv_tailoring_prompt())
        self.assertIn("json object", str(ctx.exception).lower())

    def test_parse_rejects_forbidden_full_cv_text_field(self):
        from .services import parse_cv_tailoring_semantic_payload

        payload = self._valid_cv_tailoring_payload(full_cv_text="Complete CV text here.")
        with self.assertRaises(ValueError) as ctx:
            parse_cv_tailoring_semantic_payload(payload)
        self.assertIn("full_cv_text", str(ctx.exception))

    def test_parse_rejects_forbidden_professional_summary_field(self):
        from .services import parse_cv_tailoring_semantic_payload

        payload = self._valid_cv_tailoring_payload(
            professional_summary="Experienced analyst summary."
        )
        with self.assertRaises(ValueError) as ctx:
            parse_cv_tailoring_semantic_payload(payload)
        self.assertIn("professional_summary", str(ctx.exception))

    def test_parse_rejects_forbidden_experience_bullets_field(self):
        from .services import parse_cv_tailoring_semantic_payload

        payload = self._valid_cv_tailoring_payload(
            experience_bullets=["Built dashboards end to end."]
        )
        with self.assertRaises(ValueError) as ctx:
            parse_cv_tailoring_semantic_payload(payload)
        self.assertIn("experience_bullets", str(ctx.exception))

    def test_parse_rejects_forbidden_cover_letter_body_field(self):
        from .services import parse_cv_tailoring_semantic_payload

        payload = self._valid_cv_tailoring_payload(
            cover_letter_body="Dear hiring manager, I am excited to apply."
        )
        with self.assertRaises(ValueError) as ctx:
            parse_cv_tailoring_semantic_payload(payload)
        self.assertIn("cover_letter_body", str(ctx.exception))

    def test_parse_rejects_recommended_cv_field(self):
        from .services import parse_cv_tailoring_semantic_payload

        payload = self._valid_cv_tailoring_payload(
            recommended_cv="Finance_DA_CV_v1"
        )
        with self.assertRaises(ValueError) as ctx:
            parse_cv_tailoring_semantic_payload(payload)
        self.assertIn("recommended_cv", str(ctx.exception))

    def test_parse_rejects_manual_review_required_false(self):
        from .services import parse_cv_tailoring_semantic_payload

        payload = self._valid_cv_tailoring_payload(manual_review_required=False)
        with self.assertRaises(ValueError) as ctx:
            parse_cv_tailoring_semantic_payload(payload)
        self.assertIn("manual_review_required must be true", str(ctx.exception))

    def test_parse_accepts_valid_semantic_payload(self):
        from .services import parse_cv_tailoring_semantic_payload

        result = parse_cv_tailoring_semantic_payload(self._valid_cv_tailoring_payload())
        self.assertEqual(result.semantic_matched_skills, ["python", "django"])
        self.assertEqual(result.semantic_gaps, ["dbt"])
        self.assertTrue(result.manual_review_required)
        self.assertEqual(
            result.reasoning_summary,
            "Strong Python overlap; treat dbt as a gap.",
        )

    def test_parse_claim_safety_notes_include_manual_review_language(self):
        from .services import parse_cv_tailoring_semantic_payload

        result = parse_cv_tailoring_semantic_payload(self._valid_cv_tailoring_payload())
        notes = " ".join(result.claim_safety_notes).lower()
        self.assertIn("manual review", notes)
        self.assertIn("advisory", notes)
        self.assertTrue(result.manual_review_required)


class TestCvTailoringAdvisorSemanticFallback(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="FinSight Group",
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            job_description="Python SQL Excel reporting junior",
            date_applied=date(2026, 5, 1),
        )

    def _job_fields(self):
        return {
            "company_name": "Test Co",
            "job_title": "Junior Data Analyst",
            "location": "London",
            "job_description": "Python SQL Excel reporting junior dashboard",
            "cv_evidence": "Python Django reporting",
        }

    def _valid_semantic_provider_payload(self, **overrides):
        payload = {
            "semantic_matched_skills": ["django"],
            "semantic_partial_matches": ["sql"],
            "semantic_gaps": ["dbt"],
            "semantic_project_highlights": ["BakeOps Intelligence"],
            "semantic_experience_angles": ["Operational reporting and KPI tracking"],
            "semantic_risks": ["Treat optional cloud tools as stretch goals."],
            "semantic_cover_letter_themes": [
                "Connect portfolio KPI work to reporting needs."
            ],
            "semantic_interview_points": [
                "Explain one portfolio project from problem to output."
            ],
            "reasoning_summary": "Strong Python overlap; treat dbt as a gap.",
            "claim_safety_notes": ["Semantic output is advisory only."],
            "manual_review_required": True,
        }
        payload.update(overrides)
        return payload

    def test_rule_based_output_unchanged_when_provider_callable_none(self):
        fields = self._job_fields()
        without_provider = build_cv_tailoring_advisor(**fields, provider_callable=None)
        baseline = build_cv_tailoring_advisor(**fields)
        self.assertEqual(without_provider, baseline)
        self.assertEqual(without_provider.recommended_cv, LOCKED_CV)
        self.assertNotIn(
            "Semantic enhancement unavailable",
            " ".join(without_provider.claim_safety_notes),
        )

    def test_provider_value_error_returns_rule_based_fallback(self):
        def failing_provider(prompt):
            raise ValueError("mock semantic failure")

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=failing_provider,
        )
        baseline = build_cv_tailoring_advisor(**self._job_fields())
        self.assertEqual(result.cv_angle, baseline.cv_angle)
        self.assertEqual(result.role_family, baseline.role_family)
        self.assertEqual(result.recommended_cv, LOCKED_CV)
        self.assertIn(
            "Semantic enhancement unavailable",
            " ".join(result.claim_safety_notes),
        )

    def test_provider_non_dict_returns_rule_based_fallback(self):
        def bad_provider(prompt):
            return ["not", "a", "dict"]

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=bad_provider,
        )
        self.assertIn(
            "dictionary payload",
            " ".join(result.claim_safety_notes).lower(),
        )

    def test_provider_forbidden_fields_return_rule_based_fallback(self):
        def forbidden_provider(prompt):
            return self._valid_semantic_provider_payload(full_cv_text="Complete CV.")

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=forbidden_provider,
        )
        baseline = build_cv_tailoring_advisor(**self._job_fields())
        self.assertEqual(result.matched_skills, baseline.matched_skills)
        self.assertIn(
            "Semantic enhancement unavailable",
            " ".join(result.claim_safety_notes),
        )

    def test_valid_semantic_payload_merges_claimable_strong_skills_only(self):
        def mock_provider(prompt):
            return self._valid_semantic_provider_payload(
                semantic_matched_skills=["python", "django", "dbt"],
            )

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=mock_provider,
        )
        self.assertIn("python", result.matched_skills)
        self.assertIn("django", result.matched_skills)
        self.assertNotIn("dbt", result.matched_skills)

    def test_gap_tier_skills_are_demoted_to_missing_skills_not_matched(self):
        def mock_provider(prompt):
            return self._valid_semantic_provider_payload(
                semantic_matched_skills=["snowflake", "airflow"],
                semantic_gaps=[],
            )

        result = build_cv_tailoring_advisor(
            job_title="Data Analyst",
            job_description="Python SQL snowflake airflow reporting",
            provider_callable=mock_provider,
        )
        self.assertNotIn("snowflake", result.matched_skills)
        self.assertNotIn("airflow", result.matched_skills)
        gap_text = " ".join(result.missing_skills).lower()
        self.assertTrue("snowflake" in gap_text or "airflow" in gap_text)

    def test_unknown_project_names_are_rejected(self):
        def mock_provider(prompt):
            return self._valid_semantic_provider_payload(
                semantic_project_highlights=[
                    "BakeOps Intelligence",
                    "Unknown Portfolio App",
                ],
            )

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=mock_provider,
        )
        self.assertIn("BakeOps Intelligence", result.strongest_projects)
        self.assertFalse(
            any("Unknown" in project for project in result.strongest_projects)
        )

    def test_recommended_cv_always_locked_cv_with_provider(self):
        def mock_provider(prompt):
            return self._valid_semantic_provider_payload(
                semantic_matched_skills=["python"],
            )

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=mock_provider,
        )
        self.assertEqual(result.recommended_cv, LOCKED_CV)

    def test_manual_approval_and_advisory_notes_present_after_semantic_merge(self):
        def mock_provider(prompt):
            return self._valid_semantic_provider_payload()

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=mock_provider,
        )
        self.assertIn("review and approve", result.approval_reminder.lower())
        notes = " ".join(result.claim_safety_notes).lower()
        self.assertIn("manual review", notes)
        self.assertIn("advisory", notes)
        self.assertIn("claude semantic enhancement", notes)

    def test_cover_letter_body_like_semantic_text_is_rejected_or_not_merged(self):
        def mock_provider(prompt):
            return self._valid_semantic_provider_payload(
                semantic_cover_letter_themes=[
                    "Dear hiring manager, here is my cover_letter_body draft."
                ],
            )

        result = build_cv_tailoring_advisor(
            **self._job_fields(),
            provider_callable=mock_provider,
        )
        merged_angles = " ".join(result.cover_letter_angle).lower()
        self.assertNotIn("cover_letter_body", merged_angles)
        self.assertNotIn("dear hiring manager", merged_angles)

    @override_settings(ANTHROPIC_API_KEY="")
    @patch("apps.ai_agents.views.make_claude_cv_tailoring_provider")
    def test_job_posting_analyzer_uses_rule_based_fallback_without_api_key(
        self, mock_make_provider,
    ):
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
        mock_make_provider.assert_not_called()
        self.assertContains(response, "Rule-based fallback remains active")
        self.assertContains(response, LOCKED_CV)

    @override_settings(ANTHROPIC_API_KEY="")
    @patch("apps.ai_agents.views.make_claude_cv_tailoring_provider")
    def test_application_agent_pack_uses_rule_based_fallback_without_api_key(
        self, mock_make_provider,
    ):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(
            reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk})
        )
        self.assertEqual(response.status_code, 200)
        mock_make_provider.assert_not_called()
        self.assertContains(response, "CV Tailoring Advisor")
        self.assertContains(response, "Rule-based fallback remains active")