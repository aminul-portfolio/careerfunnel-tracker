from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.models import JobApplication

from .services import get_due_followups


class FollowupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_due_followup_detected(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Test Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            follow_up_date=date(2026, 5, 2),
        )
        self.assertEqual(get_due_followups(self.user).count(), 1)

    def test_followup_page_requires_login(self):
        response = self.client.get(reverse("followups:followup_list"))
        self.assertEqual(response.status_code, 302)
