from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .services import build_dashboard_summary, get_current_week_range


class DashboardServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_current_week_range_returns_start_before_end(self):
        week_start, week_end = get_current_week_range()
        self.assertLessEqual(week_start, week_end)

    def test_dashboard_summary_without_data_returns_zero_values(self):
        summary = build_dashboard_summary(self.user)
        self.assertEqual(summary.total_applications, 0)
        self.assertEqual(summary.response_rate, 0.0)


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
