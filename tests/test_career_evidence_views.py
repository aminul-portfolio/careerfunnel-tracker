import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.dashboard import urls as dashboard_urls


class CareerEvidenceViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reviewer", password="StrongPass12345")
        self.ce_views = dashboard_urls.career_evidence_views

    def test_overview_requires_login(self):
        response = self.client.get(reverse("dashboard:career_evidence_index"))
        self.assertEqual(response.status_code, 302)

    def test_overview_returns_200_for_logged_in_user(self):
        self.client.login(username="reviewer", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:career_evidence_index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evidence viewer dashboard")
        self.assertContains(response, "V1 Project Evidence Report")

    def test_project_evidence_detail_returns_200(self):
        self.client.login(username="reviewer", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:career_evidence_project"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V1 Project Evidence Report")

    def test_job_fit_matrix_detail_returns_200(self):
        self.client.login(username="reviewer", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:career_evidence_job_fit"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V2 Job-Fit Matrix")

    def test_recruiter_pack_detail_returns_200(self):
        self.client.login(username="reviewer", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:career_evidence_recruiter"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "V3 Recruiter Evidence Pack")

    def test_missing_file_shows_warning_without_crash(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_dir = Path(tmp_dir)
            with mock.patch.object(self.ce_views, "EVIDENCE_ROOT", empty_dir):
                self.client.login(username="reviewer", password="StrongPass12345")
                response = self.client.get(reverse("dashboard:career_evidence_project"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evidence file not found")
        self.assertContains(response, "Missing")

    def test_markdown_renderer_escapes_raw_html(self):
        html_output = self.ce_views.markdown_to_safe_html("<script>alert(1)</script>")
        self.assertNotIn("<script>", html_output)
        self.assertIn("&lt;script&gt;", html_output)

    def test_no_database_models_added_for_career_evidence(self):
        module = sys.modules[self.ce_views.__name__]
        source = Path(module.__file__).read_text(encoding="utf-8")
        self.assertNotIn("models.Model", source)
        self.assertNotIn("migrate", source.lower())


if __name__ == "__main__":
    unittest.main()
