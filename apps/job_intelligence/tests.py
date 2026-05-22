from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import RoleFit, WorkType
from apps.applications.models import JobApplication

from . import constants
from .services import LOCKED_CV, build_smart_review

PHANTOM_CV_NAMES = (
    "Finance_DA_CV_v1",
    "BI_Reporting_CV_v1",
    "AE_Data_Product_CV_v1",
    "DA_CV_v2",
)


class RoleFitConstantsTests(TestCase):
    def test_constants_module_is_importable(self):
        self.assertTrue(hasattr(constants, "TARGET_TITLES"))

    def test_key_constants_are_nonempty_lists(self):
        for name in (
            "TARGET_TITLES",
            "TARGET_TITLES_AE_STRETCH",
            "BAD_TITLE_WORDS",
            "SENIOR_SIGNALS",
            "GOOD_LOCATION_WORDS",
            "GOOD_SKILLS",
            "DEAL_BREAKERS",
            "LEARNING_TARGETS",
        ):
            value = getattr(constants, name)
            self.assertIsInstance(value, list, msg=name)
            self.assertGreater(len(value), 0, msg=name)


class JobIntelligenceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _assert_locked_cv_only(self, review):
        self.assertEqual(review.recommended_cv, LOCKED_CV)
        for phantom in PHANTOM_CV_NAMES:
            self.assertNotEqual(review.recommended_cv, phantom)

    def test_smart_review_scores_good_role_at_strong_threshold(self):
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
        self._assert_locked_cv_only(review)

    def test_recommend_cv_locked_for_finance_role_text(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Northbank Finance",
            job_title="Finance Data Analyst",
            job_description="ledger reconciliation fx risk reporting analyst",
            date_applied=date(2026, 5, 10),
        )
        review = build_smart_review(application)
        self._assert_locked_cv_only(review)
        self.assertIn("finance", review.recommended_cv_reason.lower())

    def test_recommend_cv_locked_for_bi_reporting_role_text(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="ClearPath BI",
            job_title="Junior BI Dashboard Analyst",
            required_skills="power bi dashboard insights metrics",
            date_applied=date(2026, 5, 10),
        )
        review = build_smart_review(application)
        self._assert_locked_cv_only(review)
        self.assertIn("dashboard", review.recommended_cv_reason.lower())

    def test_recommend_cv_locked_for_analytics_engineering_role_text(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="DataBridge Solutions",
            job_title="Junior Analytics Engineer",
            job_description="etl pipeline api data product integration",
            date_applied=date(2026, 5, 10),
        )
        review = build_smart_review(application)
        self._assert_locked_cv_only(review)
        self.assertIn("etl", review.recommended_cv_reason.lower())

    def test_recommend_cv_locked_for_generic_data_analyst_role_text(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="BrightData Analytics",
            job_title="Junior Data Analyst",
            required_skills="Python SQL Excel",
            date_applied=date(2026, 5, 10),
        )
        review = build_smart_review(application)
        self._assert_locked_cv_only(review)
        self.assertIn("data analyst", review.recommended_cv_reason.lower())

    def test_smart_review_page_requires_login(self):
        response = self.client.get(reverse("job_intelligence:smart_review"))
        self.assertEqual(response.status_code, 302)
