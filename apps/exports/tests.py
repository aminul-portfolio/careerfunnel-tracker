from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.notes.models import Note
from apps.weekly_review.models import WeeklyReview

from .services import build_full_tracker_workbook


class ExportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_export_center_requires_login(self):
        response = self.client.get(reverse("exports:export_center"))
        self.assertEqual(response.status_code, 302)

    def test_export_center_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("exports:export_center"))
        self.assertEqual(response.status_code, 200)

    def test_applications_export_downloads_excel(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("exports:export_applications"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    def test_full_tracker_export_downloads_excel(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("exports:export_full_tracker"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


class ExportServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_full_tracker_workbook_builds_bytes(self):
        JobApplication.objects.create(user=self.user, company_name="Example Ltd", job_title="Data Analyst", date_applied=date(2026, 5, 9), status=ApplicationStatus.SUBMITTED)
        DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 9), target_applications=3, actual_applications=2)
        WeeklyReview.objects.create(user=self.user, week_starting=date(2026, 5, 4), week_ending=date(2026, 5, 10), target_applications=15, actual_applications=12)
        Note.objects.create(user=self.user, title="CV decision", content="Use Data Analyst CV version for junior roles.")
        file_bytes = build_full_tracker_workbook(self.user)
        self.assertIsInstance(file_bytes, bytes)
        self.assertGreater(len(file_bytes), 1000)
