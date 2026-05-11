from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import FollowUpStatus, WorkType
from apps.applications.models import JobApplication
from apps.interviews.models import InterviewPrep

from .services import (
    analyze_job_posting,
    build_next_best_actions,
    build_weekly_coach_report,
    generate_followup_message,
    generate_interview_prep,
)


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

    def test_job_posting_analyzer_scores_good_role(self):
        analysis = analyze_job_posting(
            company_name="FinSight",
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            job_posting="Python SQL Excel reporting dashboards junior 0-2 years",
        )
        self.assertGreaterEqual(analysis.fit_score, 70)
        self.assertIn("Finance", analysis.recommended_cv)

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
        response = self.client.get(reverse("ai_agents:application_agent_pack", kwargs={"pk": self.application.pk}))
        self.assertEqual(response.status_code, 200)


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
            cover_letter="Dear Test Co, I am applying for the Data Analyst role. My BakeOps project shows KPI reporting and dashboard analysis.",
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
        self.assertTrue(any("daily log" in n.title.lower() or "missing" in n.title.lower() for n in notifications))


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
        response = self.client.post(reverse("ai_agents:cv_gap_analyzer"), {
            "job_description": "Python SQL Excel dashboard reporting",
            "cv_evidence": "Python Excel dashboard reporting",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "CV Match Score")

    def test_cover_letter_quality_checker_view(self):
        self.client.login(username="advancedview", password="StrongPass12345")
        response = self.client.post(reverse("ai_agents:cover_letter_quality_checker"), {
            "company_name": "Test Co",
            "job_title": "Data Analyst",
            "job_description": "KPI dashboard reporting",
            "cover_letter": "Dear Test Co, I am applying for the Data Analyst role. BakeOps shows KPI dashboard reporting.",
        })
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
