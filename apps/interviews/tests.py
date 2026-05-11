from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.models import JobApplication

from .models import InterviewPrep


class InterviewPrepTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(user=self.user, company_name="Test Co", job_title="Data Analyst", date_applied=date(2026, 5, 1))

    def test_readiness_score(self):
        interview = InterviewPrep.objects.create(
            user=self.user,
            application=self.application,
            interview_date=date(2026, 5, 10),
            profile_answer_prepared=True,
            company_answer_prepared=True,
        )
        self.assertGreater(interview.readiness_score, 0)

    def test_interview_list_requires_login(self):
        response = self.client.get(reverse("interviews:interview_list"))
        self.assertEqual(response.status_code, 302)

    def test_interview_create_works(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(reverse("interviews:interview_create"), {"application": self.application.pk, "interview_date": "2026-05-10", "stage": "screening", "outcome": "scheduled"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(InterviewPrep.objects.count(), 1)
