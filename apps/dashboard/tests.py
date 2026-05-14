from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import ApplicationStatus, FollowUpStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.interviews.models import InterviewPrep

from .services import (
    TodayActionItem,
    build_dashboard_summary,
    build_today_action_panel,
    get_current_week_range,
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

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
