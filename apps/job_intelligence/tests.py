from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import RoleFit, WorkType
from apps.applications.models import JobApplication

from .services import build_smart_review


class JobIntelligenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_smart_review_scores_good_role(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Finance Co",
            job_title="Junior Finance Data Analyst",
            location="Hybrid London",
            work_type=WorkType.HYBRID,
            role_fit=RoleFit.STRONG,
            experience_level="0-2 years junior",
            required_skills="Python SQL Excel reporting dashboards finance",
            date_applied=date(2026, 5, 10),
        )
        review = build_smart_review(application)
        self.assertGreaterEqual(review.job_fit_score, 70)
        self.assertIn("Finance", review.recommended_cv)

    def test_smart_review_page_requires_login(self):
        response = self.client.get(reverse("job_intelligence:smart_review"))
        self.assertEqual(response.status_code, 302)
