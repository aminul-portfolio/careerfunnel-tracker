from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication

from .choices import FunnelDiagnosis, WeeklyMood
from .models import WeeklyReview
from .services import (
    build_weekly_review_summary,
    build_weekly_review_workflow_steps,
    suggest_diagnosis,
)


class WeeklyReviewModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_application_variance_calculates_correctly(self):
        review = WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
            target_applications=15,
            actual_applications=12,
        )
        self.assertEqual(review.application_variance, -3)

    def test_response_rate_calculates_correctly(self):
        review = WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
            actual_applications=10,
            responses_received=2,
        )
        self.assertEqual(review.response_rate, 20.0)


class WeeklyReviewViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_weekly_review_list_requires_login(self):
        response = self.client.get(reverse("weekly_review:weekly_review_list"))
        self.assertEqual(response.status_code, 302)

    def test_weekly_review_list_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("weekly_review:weekly_review_list"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_create_weekly_review(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("weekly_review:weekly_review_create"),
            {
                "week_starting": "2026-05-04",
                "week_ending": "2026-05-10",
                "target_applications": 15,
                "actual_applications": 12,
                "responses_received": 2,
                "screening_calls": 1,
                "technical_screens": 0,
                "interviews": 0,
                "offers": 0,
                "rejections": 1,
                "diagnosis": FunnelDiagnosis.SCREENING,
                "mood": WeeklyMood.STEADY,
                "what_worked": "Applied consistently.",
                "what_blocked": "Some roles were not suitable.",
                "lessons_learned": "Need stronger targeting.",
                "change_next_week": "Focus on junior roles.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(WeeklyReview.objects.filter(week_ending="2026-05-10").exists())


class WeeklyReviewServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_summary_without_reviews_returns_zero_values(self):
        summary = build_weekly_review_summary(self.user)
        self.assertEqual(summary.total_weeks_reviewed, 0)
        self.assertEqual(summary.average_response_rate, 0.0)

    def test_suggest_diagnosis_low_activity(self):
        self.assertEqual(suggest_diagnosis(0, 0, 0, 0, 0), FunnelDiagnosis.LOW_ACTIVITY)

    def test_suggest_diagnosis_cv_targeting(self):
        self.assertEqual(suggest_diagnosis(10, 0, 0, 0, 0), FunnelDiagnosis.CV_TARGETING)

    def test_suggest_diagnosis_strategy_working(self):
        self.assertEqual(suggest_diagnosis(10, 4, 2, 1, 1), FunnelDiagnosis.STRATEGY_WORKING)

    def test_workflow_steps_returns_static_copy(self):
        steps = build_weekly_review_workflow_steps()
        self.assertEqual(len(steps), 6)
        self.assertIn("Choose a funnel diagnosis manually.", steps)


class WeeklyReviewWorkflowClaimSafetyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _review_post_data(self, **overrides):
        data = {
            "week_starting": "2026-05-04",
            "week_ending": "2026-05-10",
            "target_applications": 15,
            "actual_applications": 12,
            "responses_received": 2,
            "screening_calls": 1,
            "technical_screens": 0,
            "interviews": 0,
            "offers": 0,
            "rejections": 1,
            "diagnosis": FunnelDiagnosis.SCREENING,
            "mood": WeeklyMood.STEADY,
            "what_worked": "Applied consistently.",
            "what_blocked": "Some roles were not suitable.",
            "lessons_learned": "Need stronger targeting.",
            "change_next_week": "Focus on junior roles.",
        }
        data.update(overrides)
        return data

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Workflow Co",
            "job_title": "Data Analyst",
            "date_applied": date(2026, 5, 5),
            "status": ApplicationStatus.SUBMITTED,
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_weekly_review_list_contains_manual_workflow_copy(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("weekly_review:weekly_review_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manual Workflow")
        self.assertContains(response, "manual records")
        self.assertContains(response, "does not change applications")
        self.assertContains(response, "send email")
        self.assertContains(response, "create interview prep")

    def test_weekly_review_list_links_to_weekly_coach_and_dashboard(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("weekly_review:weekly_review_list"))
        self.assertContains(response, reverse("ai_agents:weekly_coach"))
        self.assertContains(response, reverse("dashboard:overview"))

    def test_weekly_review_form_contains_manual_tracking_guidance(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("weekly_review:weekly_review_create"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manual tracking guidance")
        self.assertContains(response, "Target vs actual")
        self.assertContains(response, "does not auto-select")
        self.assertContains(response, "does not update application statuses")
        self.assertContains(response, reverse("daily_log:daily_log_list"))

    def test_weekly_review_detail_shows_lessons_learned_section(self):
        review = WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
            lessons_learned="Prioritise junior analytics roles earlier in the week.",
        )
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(review.get_absolute_url())
        self.assertContains(response, "Lessons Learned")
        self.assertContains(response, "Prioritise junior analytics roles earlier in the week.")

    def test_weekly_review_detail_links_to_dashboard_and_weekly_coach(self):
        review = WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
        )
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(review.get_absolute_url())
        self.assertContains(response, reverse("dashboard:overview"))
        self.assertContains(response, reverse("ai_agents:weekly_coach"))
        self.assertContains(response, reverse("metrics:funnel_metrics"))

    def test_weekly_review_create_does_not_create_applications(self):
        self.client.login(username="aminul", password="StrongPass12345")
        before = JobApplication.objects.filter(user=self.user).count()
        response = self.client.post(
            reverse("weekly_review:weekly_review_create"),
            self._review_post_data(),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(JobApplication.objects.filter(user=self.user).count(), before)

    def test_weekly_review_update_does_not_change_application_status(self):
        application = self._create_application(status=ApplicationStatus.SCREENING_CALL)
        review = WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
        )
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("weekly_review:weekly_review_update", kwargs={"pk": review.pk}),
            self._review_post_data(week_ending="2026-05-10", actual_applications=20),
        )
        self.assertEqual(response.status_code, 302)
        application.refresh_from_db()
        self.assertEqual(application.status, ApplicationStatus.SCREENING_CALL)

    def test_weekly_review_delete_only_removes_review_row(self):
        application = self._create_application()
        review = WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
        )
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse("weekly_review:weekly_review_delete", kwargs={"pk": review.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(WeeklyReview.objects.filter(pk=review.pk).exists())
        self.assertTrue(JobApplication.objects.filter(pk=application.pk).exists())
