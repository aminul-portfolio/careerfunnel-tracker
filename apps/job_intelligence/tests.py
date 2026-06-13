from datetime import date

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.applications.choices import (
    DocumentSource,
    DocumentStatus,
    DocumentType,
    RoleFit,
    WorkType,
)
from apps.applications.models import ApplicationDocument, JobApplication

from . import constants
from .draft_documents import (
    MASTER_CV_BASELINE,
    build_application_document_drafts,
    build_application_document_drafts_from_fields,
    build_draft_cover_letter_download_text,
    save_application_document_drafts,
)
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


class ApplicationDocumentDraftGenerationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            location="London hybrid",
            required_skills="Python SQL Excel reporting dashboards",
            job_description="Junior BI reporting role with KPI dashboards.",
            date_applied=date(2026, 5, 10),
        )

    def test_cv_draft_generation_returns_final_master_cv_baseline_name(self):
        drafts = build_application_document_drafts(self.application)
        self.assertEqual(drafts.cv_tailoring.master_cv_baseline, MASTER_CV_BASELINE)
        self.assertTrue(
            drafts.cv_tailoring.recommended_cv_filename.startswith(
                "Aminul_Islam_Data_Analyst_CV_Howden_"
            )
        )

    def test_cv_draft_generation_uses_data_analyst_bi_analyst_positioning(self):
        drafts = build_application_document_drafts(self.application)
        combined = " ".join(
            [
                drafts.cv_tailoring.headline,
                drafts.cv_tailoring.profile_angle,
            ]
        ).lower()
        self.assertIn("data analyst", combined)
        self.assertIn("bi analyst", combined)

    def test_cv_draft_generation_prioritises_bakeops_and_careerfunnel_by_default(self):
        drafts = build_application_document_drafts(
            JobApplication.objects.create(
                user=self.user,
                company_name="General Co",
                job_title="Junior Data Analyst",
                required_skills="Python SQL Excel",
                date_applied=date(2026, 5, 11),
            )
        )
        evidence_text = " ".join(drafts.recommended_project_evidence)
        bakeops_index = evidence_text.index("BakeOps Intelligence")
        careerfunnel_index = evidence_text.index("CareerFunnel Tracker")
        self.assertLess(bakeops_index, careerfunnel_index)

    def test_careerfunnel_wording_uses_skill_gap_tracking_not_skill_intelligence(self):
        drafts = build_application_document_drafts(self.application)
        evidence_text = " ".join(drafts.recommended_project_evidence).lower()
        self.assertIn("skill-gap tracking", evidence_text)
        self.assertIn("771 automated tests", evidence_text)
        self.assertNotIn("828 automated tests", evidence_text)
        self.assertNotIn("skill intelligence", evidence_text)

    def test_careerfunnel_wording_avoids_screenshot_and_saas_style_wording(self):
        drafts = build_application_document_drafts(self.application)
        combined = " ".join(
            [
                drafts.cover_letter_draft,
                " ".join(drafts.recommended_project_evidence),
                " ".join(drafts.claim_safety_notes),
            ]
        ).lower()
        self.assertNotIn("screenshot evidence", combined)
        self.assertNotIn("saas-style", combined)
        self.assertNotIn("live saas", combined)

    def test_cover_letter_draft_includes_company_and_role_title_when_available(self):
        drafts = build_application_document_drafts(self.application)
        self.assertIn("Howden", drafts.cover_letter_draft)
        self.assertIn("Junior Data Analyst", drafts.cover_letter_draft)

    def test_cover_letter_draft_is_labelled_as_draft_manual_review(self):
        drafts = build_application_document_drafts(self.application)
        self.assertIn("Draft Cover Letter", drafts.cover_letter_disclaimer)
        self.assertIn("review before use", drafts.cover_letter_disclaimer.lower())
        self.assertIn("Review before use", drafts.cover_letter_draft)

    def test_claim_safety_notes_warn_against_unsupported_claims(self):
        drafts = build_application_document_drafts_from_fields(
            job_title="Junior Analytics Engineer",
            job_description="dbt airflow pipeline required",
            required_skills="dbt airflow",
        )
        notes = " ".join(drafts.claim_safety_notes).lower()
        self.assertIn("review manually", notes)
        self.assertIn("unsupported", notes)

    def test_missing_job_data_is_handled_safely(self):
        drafts = build_application_document_drafts_from_fields()
        self.assertIn("Not enough evidence", " ".join(drafts.cv_tailoring.learning_gaps))
        self.assertIn("Review", drafts.cover_letter_draft)

    def test_generate_post_does_not_save_application_documents(self):
        before = ApplicationDocument.objects.count()
        build_application_document_drafts(self.application)
        self.client.login(username="aminul", password="StrongPass12345")
        self.client.post(
            reverse(
                "job_intelligence:application_smart_review",
                kwargs={"pk": self.application.pk},
            ),
            {"action": "generate_drafts"},
        )
        self.assertEqual(ApplicationDocument.objects.count(), before)

    def test_application_smart_review_displays_document_drafts_after_generate_post(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.post(
            reverse(
                "job_intelligence:application_smart_review",
                kwargs={"pk": self.application.pk},
            ),
            {"action": "generate_drafts"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Document Drafts")
        self.assertContains(response, "Draft CV Tailoring Notes")
        self.assertContains(response, "Draft Cover Letter")
        self.assertContains(response, "Save Drafts to Application Document Pack")


class ApplicationDocumentDraftSaveTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            location="London hybrid",
            required_skills="Python SQL Excel reporting dashboards",
            job_description="Junior BI reporting role with KPI dashboards.",
            date_applied=date(2026, 5, 10),
        )
        self.smart_review_url = reverse(
            "job_intelligence:application_smart_review",
            kwargs={"pk": self.application.pk},
        )
        self.detail_url = reverse(
            "applications:application_detail",
            kwargs={"pk": self.application.pk},
        )

    def test_save_application_document_drafts_creates_exactly_two_records(self):
        drafts = build_application_document_drafts(self.application)
        before = ApplicationDocument.objects.count()
        cv_document, cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        self.assertEqual(ApplicationDocument.objects.count(), before + 2)
        self.assertEqual(cv_document.application, self.application)
        self.assertEqual(cover_letter_document.application, self.application)

    def test_cv_draft_record_uses_document_type_cv(self):
        drafts = build_application_document_drafts(self.application)
        cv_document, _cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        self.assertEqual(cv_document.document_type, DocumentType.CV)

    def test_cover_letter_draft_record_uses_document_type_cover_letter(self):
        drafts = build_application_document_drafts(self.application)
        _cv_document, cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        self.assertEqual(cover_letter_document.document_type, DocumentType.COVER_LETTER)

    def test_saved_records_use_status_draft_and_source_job_analyzer(self):
        drafts = build_application_document_drafts(self.application)
        cv_document, cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        for document in (cv_document, cover_letter_document):
            self.assertEqual(document.status, DocumentStatus.DRAFT)
            self.assertEqual(document.source, DocumentSource.JOB_ANALYZER)

    def test_cv_record_uses_master_cv_baseline(self):
        drafts = build_application_document_drafts(self.application)
        cv_document, _cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        self.assertEqual(cv_document.cv_baseline_name, MASTER_CV_BASELINE)
        self.assertEqual(cv_document.name, drafts.cv_tailoring.recommended_cv_filename)

    def test_cv_record_content_includes_structured_tailoring_notes(self):
        drafts = build_application_document_drafts(self.application)
        cv_document, _cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        self.assertIn("Draft CV Tailoring Notes", cv_document.content)
        self.assertIn("Profile angle:", cv_document.content)
        self.assertIn("Skills to prioritise:", cv_document.tailoring_notes)

    def test_cover_letter_record_content_includes_company_and_role(self):
        drafts = build_application_document_drafts(self.application)
        _cv_document, cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        self.assertIn("Howden", cover_letter_document.content)
        self.assertIn("Junior Data Analyst", cover_letter_document.content)
        self.assertTrue(
            cover_letter_document.name.startswith("Aminul_Islam_Cover_Letter_Howden_")
        )

    def test_project_evidence_and_claim_safety_notes_are_saved(self):
        drafts = build_application_document_drafts(self.application)
        cv_document, cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        self.assertIn("BakeOps Intelligence", cv_document.project_evidence)
        self.assertIn("skill-gap tracking", cv_document.project_evidence)
        self.assertIn("Review manually", cv_document.claim_safety_notes)
        self.assertIn("Review manually", cover_letter_document.claim_safety_notes)

    def test_application_smart_review_save_post_creates_two_records(self):
        self.client.login(username="aminul", password="StrongPass12345")
        before = ApplicationDocument.objects.count()
        response = self.client.post(self.smart_review_url, {"action": "save_drafts"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ApplicationDocument.objects.count(), before + 2)
        self.assertContains(
            response,
            "Draft CV and cover letter saved to the Application Document Pack.",
        )
        self.assertContains(response, "View Application Document Pack")

    def test_application_smart_review_generate_post_does_not_save_records(self):
        self.client.login(username="aminul", password="StrongPass12345")
        before = ApplicationDocument.objects.count()
        response = self.client.post(self.smart_review_url, {"action": "generate_drafts"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(ApplicationDocument.objects.count(), before)

    def test_application_detail_page_displays_saved_document_names(self):
        drafts = build_application_document_drafts(self.application)
        save_application_document_drafts(self.application, drafts)
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Application Document Pack")
        self.assertContains(response, drafts.cv_tailoring.recommended_cv_filename)
        self.assertContains(response, "Aminul_Islam_Cover_Letter_Howden_")

    def test_no_docx_pdf_or_upload_behaviour_added(self):
        drafts = build_application_document_drafts(self.application)
        cv_document, cover_letter_document = save_application_document_drafts(
            self.application,
            drafts,
        )
        combined = " ".join(
            [
                cv_document.content,
                cover_letter_document.content,
                cv_document.claim_safety_notes,
            ]
        ).lower()
        self.assertNotIn(".docx", combined)
        self.assertNotIn(".pdf", combined)
        self.assertNotIn("upload", combined)


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


class MasterCvLockedClaimWordingTests(SimpleTestCase):
    def test_portfolio_bullet_uses_locked_master_cv_test_count(self):
        from apps.applications.master_cv import PORTFOLIO_PROJECT_BULLETS

        careerfunnel = PORTFOLIO_PROJECT_BULLETS["CareerFunnel Tracker"]
        self.assertIn("771 automated tests", careerfunnel[2])
        self.assertNotIn("828 automated tests", careerfunnel[2])


class JobPostingAnalyzerDraftDownloadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="analyzer-dl", password="StrongPass12345")
        self.analyzer_url = reverse("ai_agents:job_posting_analyzer")
        self.download_url = reverse("ai_agents:job_posting_analyzer_draft_download")
        self.post_data = {
            "company_name": "Howden",
            "job_title": "Junior Data Analyst",
            "location": "London hybrid",
            "job_posting": "Python SQL Excel reporting dashboards junior BI role",
            "generate_drafts": "1",
        }
        self.client.login(username="analyzer-dl", password="StrongPass12345")

    def test_analyzer_result_shows_draft_download_buttons_when_drafts_exist(self):
        response = self.client.post(self.analyzer_url, self.post_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Download Draft CV Notes")
        self.assertContains(response, "Download Draft Cover Letter")
        self.assertContains(response, "Draft only - review manually before use.")

    def test_cv_notes_download_returns_pdf_attachment(self):
        response = self.client.post(
            self.download_url,
            {
                **self.post_data,
                "download_kind": "cv_notes",
                "file_format": "pdf",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertIn("Draft_CV_Notes", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
        pdf_text = response.content.decode("latin-1", errors="ignore").lower()
        self.assertIn("draft cv tailoring notes", pdf_text)
        self.assertIn("review manually before use", pdf_text)
        self.assertNotIn("auto-submit", pdf_text)
        self.assertNotIn("auto-apply", pdf_text)
        self.assertNotIn("final cv", pdf_text)

    def test_cover_letter_download_returns_pdf_attachment(self):
        response = self.client.post(
            self.download_url,
            {
                **self.post_data,
                "download_kind": "cover_letter",
                "file_format": "pdf",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("Draft_Cover_Letter", response["Content-Disposition"])
        self.assertTrue(response.content.startswith(b"%PDF"))
        pdf_text = response.content.decode("latin-1", errors="ignore").lower()
        self.assertIn("draft cover letter", pdf_text)
        self.assertIn("review before use", pdf_text)
        self.assertNotIn("final cover letter", pdf_text)
        self.assertNotIn("submitted automatically", pdf_text)
        self.assertNotIn("power bi", pdf_text)
        self.assertNotIn("connect these tools to portfolio work", pdf_text)

    def test_cover_letter_download_avoids_unproven_tool_echo_when_power_bi_in_posting(self):
        response = self.client.post(
            self.download_url,
            {
                "company_name": "Howden",
                "job_title": "Junior Data Analyst",
                "location": "London hybrid",
                "job_posting": "Power BI SQL Excel reporting dashboards analytics junior role",
                "download_kind": "cover_letter",
                "file_format": "pdf",
            },
        )
        self.assertEqual(response.status_code, 200)
        pdf_text = response.content.decode("latin-1", errors="ignore").lower()
        self.assertNotIn("power bi", pdf_text)
        self.assertNotIn("connect these tools to portfolio work", pdf_text)
        self.assertIn("reporting and analytics requirements", pdf_text)

    def test_cover_letter_helper_avoids_power_bi_while_cv_notes_may_prioritise_it(self):
        drafts = build_application_document_drafts_from_fields(
            company_name="Howden",
            job_title="Junior Data Analyst",
            job_description="Power BI SQL Excel reporting dashboards analytics",
            required_skills="power bi sql excel",
        )
        cover_letter_text = build_draft_cover_letter_download_text(drafts).lower()
        self.assertNotIn("power bi", cover_letter_text)
        self.assertNotIn("connect these tools to portfolio work", cover_letter_text)
        self.assertIn("reporting and analytics requirements", cover_letter_text)
        cv_notes_text = drafts.cv_tailoring.skills_to_prioritise
        self.assertTrue(any("power bi" in skill.lower() for skill in cv_notes_text))

    def test_application_pack_download_uses_existing_pack_renderer(self):
        response = self.client.post(
            self.download_url,
            {
                **self.post_data,
                "download_kind": "application_pack",
                "file_format": "pdf",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Draft_Application_Pack", response["Content-Disposition"])
        pdf_text = response.content.decode("latin-1", errors="ignore").lower()
        self.assertIn("draft application pack", pdf_text)
        self.assertIn("claim-safety notes", pdf_text)

    def test_download_requires_post(self):
        response = self.client.get(self.download_url)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.analyzer_url)
