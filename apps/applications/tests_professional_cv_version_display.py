from __future__ import annotations

import re
from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from apps.applications.choices import DEFAULT_CV_BASELINE_NAME, PipelineStage
from apps.applications.file_storage import build_professional_cv_basename
from apps.applications.services import (
    build_application_cv_version_display,
    display_application_cv_version_for_application,
    display_evaluation_cv_label,
)
from apps.job_intelligence.draft_documents import (
    build_application_document_drafts,
    build_complete_cv_content,
)

from .choices import DocumentType
from .models import ApplicationDocument, JobApplication

FORBIDDEN_TOKENS = (
    "Response57",
    "Interview14",
    "Promising",
    "Underperforming",
    "NoABData",
    "careerfunnel_",
)


class ProfessionalCvBasenameTests(SimpleTestCase):
    def test_basename_matches_required_format(self):
        basename = build_professional_cv_basename(
            "Howden",
            "Junior Data Analyst",
            reference_date=date(2026, 5, 31),
        )
        self.assertEqual(basename, "Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260531")

    def test_basename_uses_company_role_date_and_excludes_ab_metrics(self):
        basename = build_professional_cv_basename(
            "Monzo",
            "Data Analyst",
            reference_date=date(2026, 5, 31),
        )
        self.assertIn("Aminul_Islam", basename)
        self.assertIn("Monzo", basename)
        self.assertIn("Data_Analyst", basename)
        self.assertIn("20260531", basename)
        for token in FORBIDDEN_TOKENS:
            self.assertNotIn(token, basename)


class ApplicationCvVersionDisplayServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cv-display", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
            cv_version="DA_CV_v2",
        )

    def test_application_readiness_display_uses_date_applied(self):
        display = build_application_cv_version_display(self.application)
        self.assertEqual(
            display.professional_basename,
            "Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260509",
        )
        self.assertEqual(display.internal_baseline, "DA_CV_v2")

    def test_evaluation_cv_label_matches_professional_basename(self):
        label = display_evaluation_cv_label(
            application=self.application,
            cv_document_available=False,
        )
        self.assertEqual(label, display_application_cv_version_for_application(self.application))

    def test_professional_basename_has_no_unsafe_characters(self):
        display = build_application_cv_version_display(self.application)
        self.assertIsNone(re.search(r"[^A-Za-z0-9_]", display.professional_basename))


class ApplicationCvVersionDisplayViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cv-display-view", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Howden",
            job_title="Junior Data Analyst",
            date_applied=date(2026, 5, 9),
            pipeline_stage=PipelineStage.FIT_CHECKED,
            cv_version="DA_CV_v2",
        )
        self.client.login(username="cv-display-view", password="StrongPass12345")

    def test_application_detail_shows_professional_cv_version_and_internal_baseline(self):
        response = self.client.get(self.application.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260509",
        )
        self.assertContains(response, "Internal baseline: DA_CV_v2")
        for token in FORBIDDEN_TOKENS:
            self.assertNotContains(response, token)

    @patch("apps.applications.file_storage.timezone.localdate", return_value=date(2026, 5, 31))
    def test_application_create_prefill_shows_professional_cv_basename(self, _mock_date):
        response = self.client.get(
            reverse("applications:application_create")
            + "?company_name=Howden&job_title=Junior+Data+Analyst"
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260531",
        )
        self.assertContains(response, f"Internal baseline: {DEFAULT_CV_BASELINE_NAME}")
        self.assertContains(response, 'name="cv_version"')
        self.assertContains(response, f'value="{DEFAULT_CV_BASELINE_NAME}"')
        for token in FORBIDDEN_TOKENS:
            self.assertNotContains(response, token)

    def test_evaluation_queue_shows_professional_cv_basename(self):
        drafts = build_application_document_drafts(self.application)
        ApplicationDocument.objects.create(
            application=self.application,
            document_type=DocumentType.CV,
            name=drafts.cv_tailoring.recommended_cv_filename,
            content=build_complete_cv_content(self.application, drafts),
        )
        response = self.client.get(reverse("applications:evaluation_queue"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Aminul_Islam_CV_Howden_Junior_Data_Analyst_20260509",
        )
        for token in FORBIDDEN_TOKENS:
            self.assertNotContains(response, token)

