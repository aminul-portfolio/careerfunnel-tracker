from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .choices import FunnelDiagnosis, WeeklyMood
from .models import WeeklyReview
from .services import build_weekly_review_summary, suggest_diagnosis


class WeeklyReviewModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_application_variance_calculates_correctly(self):
        review = WeeklyReview.objects.create(user=self.user, week_starting=date(2026, 5, 4), week_ending=date(2026, 5, 10), target_applications=15, actual_applications=12)
        self.assertEqual(review.application_variance, -3)

    def test_response_rate_calculates_correctly(self):
        review = WeeklyReview.objects.create(user=self.user, week_starting=date(2026, 5, 4), week_ending=date(2026, 5, 10), actual_applications=10, responses_received=2)
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
        response = self.client.post(reverse("weekly_review:weekly_review_create"), {"week_starting": "2026-05-04", "week_ending": "2026-05-10", "target_applications": 15, "actual_applications": 12, "responses_received": 2, "screening_calls": 1, "technical_screens": 0, "interviews": 0, "offers": 0, "rejections": 1, "diagnosis": FunnelDiagnosis.SCREENING, "mood": WeeklyMood.STEADY, "what_worked": "Applied consistently.", "what_blocked": "Some roles were not suitable.", "lessons_learned": "Need stronger targeting.", "change_next_week": "Focus on junior roles."})
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
