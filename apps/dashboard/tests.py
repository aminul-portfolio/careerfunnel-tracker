from datetime import date, timedelta
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
    build_today_action_panel,
    get_current_week_range,
    should_prompt_weekly_review,
)


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

    def test_today_action_panel_returns_empty_when_nothing_needs_attention(self):
        DailyLog.objects.create(user=self.user, log_date=timezone.localdate())

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
        self.assertContains(response, "Today Action Panel")

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
        self.assertContains(response, "High - Overdue follow-up: Action Co")
        self.assertContains(response, "Send a short follow-up and update the follow-up status.")
        self.assertContains(response, application.get_absolute_url())

    def test_dashboard_displays_today_action_panel_empty_state(self):
        DailyLog.objects.create(user=self.user, log_date=timezone.localdate())

        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_action_panel"], [])
        self.assertContains(response, "Nothing urgent needs attention right now.")


class DashboardWeeklyOsPolishTests(TestCase):
    WEEK_END_SUNDAY = date(2026, 5, 10)

    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_dashboard_contains_weekly_operating_rhythm_copy(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weekly operating rhythm")
        self.assertContains(response, "Manual rhythm only")
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
