from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog

from .services import build_funnel_metrics, diagnose_funnel, safe_percentage


class MetricsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_safe_percentage_returns_zero_when_denominator_is_zero(self):
        self.assertEqual(safe_percentage(5, 0), 0.0)

    def test_safe_percentage_calculates_correctly(self):
        self.assertEqual(safe_percentage(2, 10), 20.0)

    def test_metrics_without_data_returns_zero_values(self):
        metrics = build_funnel_metrics(self.user)
        self.assertEqual(metrics.total_applications, 0)
        self.assertEqual(metrics.response_rate, 0.0)

    def test_metrics_calculates_application_counts(self):
        JobApplication.objects.create(user=self.user, company_name="Company A", job_title="Data Analyst", date_applied=date(2026, 5, 1), status=ApplicationStatus.SUBMITTED)
        JobApplication.objects.create(user=self.user, company_name="Company B", job_title="BI Analyst", date_applied=date(2026, 5, 2), status=ApplicationStatus.ACKNOWLEDGED)
        JobApplication.objects.create(user=self.user, company_name="Company C", job_title="Reporting Analyst", date_applied=date(2026, 5, 3), status=ApplicationStatus.INTERVIEW)
        metrics = build_funnel_metrics(self.user)
        self.assertEqual(metrics.total_applications, 3)
        self.assertEqual(metrics.response_count, 2)
        self.assertEqual(metrics.response_rate, 66.67)

    def test_metrics_calculates_daily_log_totals(self):
        DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 9), target_applications=3, actual_applications=2, hours_spent=Decimal("2.50"), energy_level=4)
        DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 10), target_applications=3, actual_applications=3, hours_spent=Decimal("3.00"), energy_level=4)
        metrics = build_funnel_metrics(self.user)
        self.assertEqual(metrics.daily_target_total, 6)
        self.assertEqual(metrics.daily_actual_total, 5)
        self.assertEqual(metrics.daily_target_hit_rate, 50.0)

    def test_diagnosis_without_applications(self):
        diagnosis = diagnose_funnel(build_funnel_metrics(self.user))
        self.assertEqual(diagnosis.diagnosis_label, "Unknown / not enough data")


class MetricsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_funnel_metrics_requires_login(self):
        response = self.client.get(reverse("metrics:funnel_metrics"))
        self.assertEqual(response.status_code, 302)

    def test_funnel_metrics_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("metrics:funnel_metrics"))
        self.assertEqual(response.status_code, 200)
