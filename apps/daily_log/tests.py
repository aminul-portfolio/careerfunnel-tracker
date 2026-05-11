from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import DailyLog
from .services import build_daily_log_summary


class DailyLogModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_variance_calculates_correctly(self):
        log = DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 9), target_applications=3, actual_applications=1)
        self.assertEqual(log.variance, -2)

    def test_target_met_returns_true_when_actual_equals_target(self):
        log = DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 9), target_applications=3, actual_applications=3)
        self.assertTrue(log.target_met)

    def test_activity_signal_below_target(self):
        log = DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 9), target_applications=3, actual_applications=1)
        self.assertEqual(log.activity_signal, "Below target")


class DailyLogViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_daily_log_list_requires_login(self):
        response = self.client.get(reverse("daily_log:daily_log_list"))
        self.assertEqual(response.status_code, 302)

    def test_daily_log_list_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("daily_log:daily_log_list"))
        self.assertEqual(response.status_code, 200)

    def test_user_can_create_daily_log(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(reverse("daily_log:daily_log_create"), {"log_date": "2026-05-09", "target_applications": 3, "actual_applications": 2, "cover_letters_drafted": 2, "responses_received": 1, "calls_received": 0, "hours_spent": "2.50", "energy_level": 4, "notes": "Good application quality."})
        self.assertEqual(response.status_code, 302)
        self.assertTrue(DailyLog.objects.filter(log_date="2026-05-09").exists())


class DailyLogServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_summary_without_logs_returns_zero_values(self):
        summary = build_daily_log_summary(self.user)
        self.assertEqual(summary.total_days_logged, 0)
        self.assertEqual(summary.target_hit_rate, 0.0)

    def test_summary_calculates_totals(self):
        DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 9), target_applications=3, actual_applications=3, cover_letters_drafted=2, responses_received=1, hours_spent=Decimal("2.50"), energy_level=4)
        DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 10), target_applications=3, actual_applications=1, cover_letters_drafted=1, hours_spent=Decimal("1.50"), energy_level=3)
        summary = build_daily_log_summary(self.user)
        self.assertEqual(summary.total_days_logged, 2)
        self.assertEqual(summary.total_target_applications, 6)
        self.assertEqual(summary.total_actual_applications, 4)
        self.assertEqual(summary.total_variance, -2)
        self.assertEqual(summary.target_hit_rate, 50.0)
