from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import ApplicationStatus, FollowUpStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.interviews.models import InterviewPrep
from apps.weekly_review.models import WeeklyReview

from .services import (
    TodayActionItem,
    build_dashboard_summary,
    build_evidence_readiness_summary,
    build_pipeline_health_matrix,
    build_recent_activity_timeline,
    build_today_action_panel,
    build_today_signals,
    build_week_pulse,
    get_current_week_range,
    should_prompt_weekly_review,
)

# Wednesday - not week-ending (Sunday), so empty-state tests stay CI-stable.
STABLE_NON_WEEK_END = date(2026, 5, 20)


class DashboardServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Test Company",
            "job_title": "Data Analyst",
            "job_url": "https://example.com/job",
            "required_skills": "SQL, Python",
            "job_description": "Analyse operational data and report findings.",
            "date_applied": timezone.localdate() - timedelta(days=7),
            "cv_version": "Data_CV_v1",
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_current_week_range_returns_start_before_end(self):
        week_start, week_end = get_current_week_range()
        self.assertLessEqual(week_start, week_end)

    def test_dashboard_summary_without_data_returns_zero_values(self):
        summary = build_dashboard_summary(self.user)
        self.assertEqual(summary.total_applications, 0)
        self.assertEqual(summary.response_rate, 0.0)

    def test_today_action_panel_identifies_rule_based_actions(self):
        today = timezone.localdate()
        overdue = self._create_application(
            company_name="Overdue Co",
            follow_up_date=today - timedelta(days=2),
            follow_up_status=FollowUpStatus.DUE,
        )
        self._create_application(
            company_name="Today Co",
            follow_up_date=today,
            follow_up_status=FollowUpStatus.NOT_SET,
        )
        self._create_application(
            company_name="Missing Data Co",
            cv_version="",
            job_url="",
            required_skills="",
            job_description="",
        )
        interview_application = self._create_application(
            company_name="Interview Co",
            status=ApplicationStatus.INTERVIEW,
        )
        InterviewPrep.objects.create(
            user=self.user,
            application=interview_application,
            interview_date=today + timedelta(days=2),
        )

        actions = build_today_action_panel(self.user, limit=8)
        titles = [action.title for action in actions]
        priority_rank = {"High": 0, "Medium": 1, "Low": 2}

        self.assertTrue(all(isinstance(action, TodayActionItem) for action in actions))
        self.assertIn("Overdue follow-up: Overdue Co", titles)
        self.assertIn("Follow up today: Today Co", titles)
        self.assertIn("Prepare for interview: Interview Co", titles)
        self.assertIn("Add CV version: Missing Data Co", titles)
        self.assertIn("Add job evidence: Missing Data Co", titles)
        self.assertIn("Add job URL: Missing Data Co", titles)
        self.assertIn("Add today's daily log", titles)
        self.assertIn(overdue.get_absolute_url(), [action.related_url for action in actions])
        self.assertEqual(
            [priority_rank[action.priority] for action in actions],
            sorted(priority_rank[action.priority] for action in actions),
        )

    def test_today_action_panel_respects_limit_after_priority_sorting(self):
        today = timezone.localdate()
        DailyLog.objects.create(user=self.user, log_date=today)
        self._create_application(company_name="Low Priority Co", job_url="")
        self._create_application(
            company_name="High Priority Co",
            follow_up_date=today - timedelta(days=1),
            follow_up_status=FollowUpStatus.DUE,
        )

        actions = build_today_action_panel(self.user, limit=1)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].priority, "High")
        self.assertEqual(actions[0].title, "Overdue follow-up: High Priority Co")

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_today_action_panel_returns_empty_when_nothing_needs_attention(
        self, _mock_localdate
    ):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)

        actions = build_today_action_panel(self.user)

        self.assertEqual(actions, [])


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Dashboard Co",
            "job_title": "Data Analyst",
            "job_url": "https://example.com/dashboard-job",
            "required_skills": "SQL, Python",
            "job_description": "Build dashboards and explain trends.",
            "date_applied": timezone.localdate() - timedelta(days=7),
            "cv_version": "Data_CV_v1",
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("today_action_panel", response.context)
        self.assertContains(response, "Today Signals")

    def test_dashboard_displays_today_action_panel_item(self):
        today = timezone.localdate()
        DailyLog.objects.create(user=self.user, log_date=today)
        application = self._create_application(
            company_name="Action Co",
            follow_up_date=today - timedelta(days=1),
            follow_up_status=FollowUpStatus.DUE,
        )

        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overdue follow-up: Action Co")
        self.assertContains(response, "Send a short follow-up and update the follow-up status.")
        self.assertContains(response, application.get_absolute_url())

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_dashboard_displays_today_action_panel_empty_state(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)

        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_action_panel"], [])
        self.assertContains(response, "Command centre clear")


class DashboardWeeklyOsPolishTests(TestCase):
    WEEK_END_SUNDAY = date(2026, 5, 10)

    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_dashboard_contains_weekly_operating_rhythm_copy(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weekly Operating Pipeline")
        self.assertContains(response, "Manual rhythm only")
        self.assertContains(response, "Capture")
        self.assertContains(response, reverse("daily_log:daily_log_list"))
        self.assertContains(response, reverse("weekly_review:weekly_review_list"))
        self.assertContains(response, reverse("ai_agents:weekly_coach"))

    @patch("apps.dashboard.services.timezone.localdate", return_value=WEEK_END_SUNDAY)
    def test_today_action_includes_weekly_review_prompt_on_week_end(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=self.WEEK_END_SUNDAY)
        actions = build_today_action_panel(self.user)
        titles = [action.title for action in actions]
        self.assertIn("Weekly review due", titles)

    @patch("apps.dashboard.services.timezone.localdate", return_value=WEEK_END_SUNDAY)
    def test_today_action_weekly_review_prompt_links_to_create(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=self.WEEK_END_SUNDAY)
        actions = build_today_action_panel(self.user)
        weekly_actions = [action for action in actions if action.title == "Weekly review due"]
        self.assertEqual(len(weekly_actions), 1)
        self.assertEqual(
            weekly_actions[0].related_url,
            reverse("weekly_review:weekly_review_create"),
        )
        self.assertIn("manual weekly review", weekly_actions[0].recommended_action)

    @patch("apps.dashboard.services.timezone.localdate", return_value=WEEK_END_SUNDAY)
    def test_today_action_weekly_review_prompt_not_shown_when_review_exists(
        self, _mock_localdate
    ):
        DailyLog.objects.create(user=self.user, log_date=self.WEEK_END_SUNDAY)
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=self.WEEK_END_SUNDAY,
        )
        self.assertFalse(should_prompt_weekly_review(self.user, self.WEEK_END_SUNDAY))
        actions = build_today_action_panel(self.user)
        titles = [action.title for action in actions]
        self.assertNotIn("Weekly review due", titles)

    def test_dashboard_get_does_not_mutate_applications_or_weekly_reviews(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Stable Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
        )
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 4, 27),
            week_ending=date(2026, 5, 3),
        )
        application_count_before = JobApplication.objects.filter(user=self.user).count()
        review_count_before = WeeklyReview.objects.filter(user=self.user).count()
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            JobApplication.objects.filter(user=self.user).count(),
            application_count_before,
        )
        self.assertEqual(
            WeeklyReview.objects.filter(user=self.user).count(),
            review_count_before,
        )

    def test_dashboard_copy_remains_manual_and_claim_safe(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "does not submit applications")
        self.assertContains(response, "send email")
        self.assertContains(response, "update statuses automatically")
        self.assertContains(response, "interview prep automatically")
        self.assertContains(response, "For week-level reflection")
        self.assertContains(response, "advisory risks")
        self.assertContains(response, "does not submit applications")


class DashboardCommandCentrePolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.client.login(username="aminul", password="StrongPass12345")

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Command Co",
            "job_title": "Data Analyst",
            "job_url": "https://example.com/job",
            "required_skills": "SQL, Python",
            "job_description": "Analyze operational data.",
            "date_applied": timezone.localdate(),
            "cv_version": "Aminul_Islam_Data_Analyst_CV",
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_dashboard_renders_career_command_centre_copy(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics Command Centre")
        self.assertContains(response, "Calm authority for the manual job-search pipeline")
        self.assertContains(response, "Signature Career Insight")

    def test_dashboard_shows_week_pulse(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("week_pulse", response.context)
        self.assertContains(response, "Week Pulse")
        self.assertContains(response, response.context["week_pulse"].week_range_label)

    def test_dashboard_shows_pipeline_health_matrix(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("pipeline_health", response.context)
        self.assertContains(response, "Pipeline Health Matrix")
        self.assertEqual(len(response.context["pipeline_health"].metrics), 6)

    def test_dashboard_shows_evidence_readiness_summary(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("evidence_readiness", response.context)
        self.assertContains(response, "Evidence Readiness")
        self.assertContains(response, "Missing CV versions")

    def test_dashboard_today_signals_remain_manual_and_claim_safe(self):
        today = timezone.localdate()
        DailyLog.objects.create(user=self.user, log_date=today)
        self._create_application(
            company_name="Signal Co",
            follow_up_date=today - timedelta(days=1),
            follow_up_status=FollowUpStatus.DUE,
        )
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("today_signals", response.context)
        self.assertContains(response, "Today Signals")
        self.assertContains(response, "Send a short follow-up and update the follow-up status.")
        self.assertContains(response, "Open")

    def test_dashboard_get_does_not_mutate_records(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Stable Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
        )
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 4, 27),
            week_ending=date(2026, 5, 3),
        )
        application_count_before = JobApplication.objects.filter(user=self.user).count()
        review_count_before = WeeklyReview.objects.filter(user=self.user).count()
        log_count_before = DailyLog.objects.filter(user=self.user).count()
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            JobApplication.objects.filter(user=self.user).count(),
            application_count_before,
        )
        self.assertEqual(
            WeeklyReview.objects.filter(user=self.user).count(),
            review_count_before,
        )
        self.assertEqual(DailyLog.objects.filter(user=self.user).count(), log_count_before)

    def test_dashboard_links_to_manual_workflow_pages(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        for url_name in (
            "applications:application_create",
            "daily_log:daily_log_create",
            "weekly_review:weekly_review_create",
            "metrics:funnel_metrics",
            "followups:followup_list",
            "interviews:interview_list",
        ):
            with self.subTest(url_name=url_name):
                self.assertContains(response, reverse(url_name))

    def test_dashboard_phase_69a_loads_without_error_for_authenticated_user(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_phase_69a_preserves_reviewer_walkthrough_wording(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Reviewer walkthrough")
        self.assertContains(response, "How to assess this portfolio project")
        self.assertContains(response, "manual, advisory, deterministic job-search analytics app")
        self.assertContains(response, "Deliberately not implemented")

    def test_dashboard_phase_69a_preserves_manual_advisory_wording(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Manual workflow only")
        self.assertContains(response, "Advisory guidance")
        self.assertContains(response, "Open manual workflow")
        self.assertContains(response, "Manual rhythm only")

    def test_dashboard_phase_69a_preserves_deterministic_rule_based_wording(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Deterministic records")
        self.assertContains(response, "rule-based from saved applications")
        self.assertContains(response, "Calculated from authenticated tracker records")

    def test_dashboard_phase_69a_kpi_values_render_from_context(self):
        self._create_application(status=ApplicationStatus.ACKNOWLEDGED)
        response = self.client.get(reverse("dashboard:overview"))
        summary = response.context["summary"]
        self.assertContains(response, "Total Applications")
        self.assertContains(response, f">{summary.total_applications}<")
        self.assertContains(response, f">{summary.applications_this_week}<")
        self.assertContains(response, f">{summary.response_rate}%<")
        self.assertContains(response, f">{summary.interview_rate}%<")

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_dashboard_phase_69a_today_signals_or_safe_empty_state_renders(
        self, _mock_localdate
    ):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Today Signals")
        content = response.content.decode()
        self.assertTrue(
            "Command centre clear" in content
            or "Nothing urgent needs attention right now." in content
        )

    def test_dashboard_phase_69a_funnel_snapshot_values_render(self):
        self._create_application(status=ApplicationStatus.INTERVIEW)
        response = self.client.get(reverse("dashboard:overview"))
        snapshot = response.context["funnel_snapshot"]
        self.assertContains(response, "Funnel Snapshot")
        self.assertContains(response, f">{snapshot.applications}<")
        self.assertContains(response, f">{snapshot.responses}<")
        self.assertContains(response, f">{snapshot.interviews}<")
        self.assertContains(response, f">{snapshot.offers}<")

    def test_dashboard_phase_69a_week_pulse_values_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        week_pulse = response.context["week_pulse"]
        self.assertContains(response, "Week Pulse")
        self.assertContains(response, week_pulse.week_range_label)
        self.assertContains(response, f">{week_pulse.target_applications}<")
        self.assertContains(response, f">{week_pulse.actual_applications}<")
        self.assertContains(response, f">{week_pulse.variance}<")

    def test_dashboard_phase_69a_evidence_readiness_values_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        readiness = response.context["evidence_readiness"]
        self.assertContains(response, "Evidence Readiness")
        self.assertContains(response, f">{readiness.missing_cv_versions}<")
        self.assertContains(response, f">{readiness.missing_job_descriptions}<")
        self.assertContains(response, "Data Quality Report")

    def test_dashboard_phase_69a_signature_insight_renders_when_present(self):
        response = self.client.get(reverse("dashboard:overview"))
        insight = response.context["signature_insight"]
        self.assertContains(response, "Signature Career Insight")
        content = response.content.decode()
        self.assertIn(insight.diagnosis.replace("'", "&#x27;"), content)
        self.assertIn(insight.best_manual_action.replace("'", "&#x27;"), content)

    def test_dashboard_phase_69a_does_not_render_invented_trend_indicators(self):
        response = self.client.get(reverse("dashboard:overview"))
        content = response.content.decode().lower()
        forbidden_trends = (
            "% increase",
            "% decrease",
            "trending up",
            "trending down",
            "upward trend",
            "downward trend",
        )
        for phrase in forbidden_trends:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_dashboard_phase_69a_unsafe_positive_action_labels_are_absent(self):
        response = self.client.get(reverse("dashboard:overview"))
        content = response.content.decode()
        unsafe_labels = (
            "Apply Now",
            "Submit Application",
            "Auto Apply",
            "Send Application",
        )
        for label in unsafe_labels:
            with self.subTest(label=label):
                self.assertNotIn(f">{label}<", content)

    def test_dashboard_phase_69a_safe_manual_action_labels_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        for label in (
            "Log Application",
            "Weekly Review",
            "Follow-up Tracker",
            "Interview Prep",
            "Funnel Metrics",
            "Data Quality Report",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_dashboard_phase_69a_scoped_zone_and_advisory_classes_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        for class_name in (
            "cf69-zone-command",
            "cf69-zone-today",
            "cf69-zone-intelligence",
            "cf69-zone-actions",
            "cf69-advisory-info",
            "cf69-advisory-manual",
            "cf69-advisory-warning",
        ):
            with self.subTest(class_name=class_name):
                self.assertContains(response, class_name)

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_dashboard_empty_state_for_new_user(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Command centre clear")
        self.assertContains(response, "Recent Activity Timeline")
        self.assertContains(response, "Daily Log")
        self.assertEqual(build_week_pulse(self.user).target_applications, 0)
        self.assertEqual(build_evidence_readiness_summary(self.user).missing_cv_versions, 0)

    def test_dashboard_shows_recent_activity_timeline(self):
        application = self._create_application(company_name="Timeline Co")
        DailyLog.objects.create(
            user=self.user,
            log_date=timezone.localdate(),
            target_applications=2,
            actual_applications=1,
        )
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("recent_activity_timeline", response.context)
        self.assertContains(response, "Recent Activity Timeline")
        self.assertContains(response, "Timeline Co")
        timeline = build_recent_activity_timeline(self.user)
        self.assertTrue(any(item.title == application.company_name for item in timeline))

    def test_dashboard_shows_funnel_snapshot(self):
        self._create_application(status=ApplicationStatus.ACKNOWLEDGED)
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("funnel_snapshot", response.context)
        self.assertContains(response, "Funnel Snapshot")
        self.assertContains(response, "Applications")
        self.assertContains(response, "Responses")
        self.assertContains(response, "Interviews")
        self.assertContains(response, "Offers")

    def test_dashboard_does_not_claim_automation_or_live_saas(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "does not submit applications")
        self.assertContains(response, "send email")
        self.assertContains(response, "update statuses automatically")
        self.assertContains(response, "create interview prep automatically")
        self.assertContains(response, "auto-apply")
        self.assertContains(response, "background polling")
        self.assertContains(response, "live SaaS deployment")

    def test_build_pipeline_health_matrix_returns_six_metrics(self):
        matrix = build_pipeline_health_matrix(self.user)
        labels = [metric.label for metric in matrix.metrics]
        self.assertEqual(
            labels,
            [
                "Activity volume",
                "Evidence quality",
                "Follow-up discipline",
                "Interview readiness",
                "Weekly review discipline",
                "Response conversion",
            ],
        )

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_build_today_signals_adds_info_when_no_urgent_actions(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)
        signals = build_today_signals(self.user)
        self.assertEqual(signals[0].priority, "Info")
        self.assertIn("Command centre clear", signals[0].title)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Sprint51ReviewerWalkthroughPolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="revdash", password="StrongPass12345")

    def test_dashboard_renders_reviewer_walkthrough_copy(self):
        self.client.login(username="revdash", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reviewer walkthrough")
        self.assertContains(response, "How to assess this portfolio project")
        self.assertContains(response, "Skill Intelligence Dashboard")
        self.assertContains(response, "Deliberately not implemented")

    def test_sprint_51_reviewer_copy_remains_claim_safe(self):
        self.client.login(username="revdash", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        content = response.content.decode().lower()
        self.assertIn("manual workflow only", content)
        self.assertIn("deliberately not implemented", content)
        self.assertIn("automatic application submission", content)
        self.assertIn("automatic cv rewriting", content)
        self.assertNotIn("sprint 52", content)

    def test_no_sprint_52_text_on_dashboard_home(self):
        self.client.login(username="revdash", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertNotContains(response, "Sprint 52")

    def test_sprint_51_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "templates" / "dashboard" / "overview.html",
            REPO_ROOT / "docs" / "evidence" / "sprint_51_final_reviewer_walkthrough_polish.md",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )
