from __future__ import annotations

import re
from datetime import date

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from apps.applications.file_storage import build_professional_cv_basename
from apps.applications.services import (
    build_application_cv_version_display,
    display_application_cv_version_for_application,
    display_evaluation_cv_label,
)

from .models import JobApplication

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
