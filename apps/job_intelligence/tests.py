from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import RoleFit, WorkType
from apps.applications.models import JobApplication

from . import constants
from .services import LOCKED_CV, build_skill_intelligence_context, build_smart_review

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


class SkillIntelligenceFoundationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.url = reverse("job_intelligence:skill_intelligence")

    def _login(self):
        self.client.login(username="aminul", password="StrongPass12345")

    def _get(self):
        self._login()
        return self.client.get(self.url)

    def _create_app(self, **kwargs):
        defaults = {
            "user": self.user,
            "company_name": "Acme",
            "job_title": "Junior Data Analyst",
            "date_applied": date(2026, 5, 10),
            "required_skills": "",
            "job_description": "",
        }
        defaults.update(kwargs)
        return JobApplication.objects.create(**defaults)

    def test_skill_intelligence_page_renders(self):
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertIn("skill_intelligence", response.context)
        self.assertContains(response, "Skill Intelligence")

    def test_skill_evidence_summary_renders(self):
        self._create_app(
            required_skills="Python SQL Excel dashboards",
            job_description="data analysis reporting",
        )
        response = self._get()
        content = response.content.decode()
        self.assertIn("Skill Evidence Summary", content)
        self.assertIn("Python", content)
        self.assertIn("not automatic AI extraction", content)

    def test_skill_gap_review_renders(self):
        self._create_app(required_skills="niche domain only", job_description="specialist")
        response = self._get()
        self.assertContains(response, "Skill Gap Review")
        self.assertContains(response, "manually before applying")

    def test_role_readiness_checklist_renders_for_all_role_families(self):
        response = self._get()
        content = response.content.decode()
        self.assertIn("Data Analyst", content)
        self.assertIn("BI Analyst", content)
        self.assertIn("Analytics Engineer", content)
        self.assertIn("Data Engineer", content)
        self.assertIn("No numeric job-fit score", content)

    def test_portfolio_evidence_mapping_renders(self):
        response = self._get()
        self.assertContains(response, "Portfolio Evidence Mapping")
        self.assertContains(response, "CareerFunnel Tracker")
        self.assertContains(response, "Open manually")

    def test_get_request_does_not_mutate_records(self):
        self._create_app(required_skills="Python SQL")
        count_before = JobApplication.objects.filter(user=self.user).count()
        response = self._get()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            JobApplication.objects.filter(user=self.user).count(),
            count_before,
        )

    def test_no_sprint_42_copy_present(self):
        response = self._get()
        content = response.content.decode()
        self.assertNotIn("Sprint 42", content)

    def test_claim_safety_wording_remains_clean(self):
        response = self._get()
        content = response.content.decode().lower()
        self.assertIn("manual", content)
        self.assertIn("advisory", content)
        self.assertIn("evidence-based", content)
        self.assertIn("read-only", content)
        self.assertIn("does not make hiring decisions", content)
        self.assertIn("rewrite cvs", content)
        self.assertIn("predictive ai", content)
        self.assertNotIn("auto-apply enabled", content)
        self.assertNotIn("automatic application submission", content)
        self.assertNotIn("automatic cv rewriting enabled", content)
        self.assertNotIn("gmail integration", content)
        self.assertNotIn("oauth", content)
        self.assertNotIn("web scraping", content)
        self.assertNotIn("live saas users", content)
        self.assertNotIn("production deployment", content)
        self.assertNotIn("machine learning model", content)

    def test_skill_intelligence_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_build_skill_intelligence_context_returns_expected_roles(self):
        context = build_skill_intelligence_context(self.user)
        role_titles = {role.role_title for role in context.role_checklists}
        self.assertEqual(
            role_titles,
            {"Data Analyst", "BI Analyst", "Analytics Engineer", "Data Engineer"},
        )
        self.assertEqual(len(context.skill_evidence), 10)

    def test_no_models_or_migrations_required(self):
        import importlib.util

        self.assertIsNone(importlib.util.find_spec("apps.job_intelligence.models"))
