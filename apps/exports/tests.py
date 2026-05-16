import csv
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import (
    ApplicationSource,
    ApplicationStatus,
    FollowUpStatus,
    PipelineStage,
    RoleFit,
    WorkType,
)
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.notes.models import Note
from apps.weekly_review.models import WeeklyReview

from .services import build_full_tracker_workbook

XLSX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXPORT_ROUTE_NAMES = [
    "exports:export_center",
    "exports:export_applications",
    "exports:export_daily_logs",
    "exports:export_weekly_reviews",
    "exports:export_interviews",
    "exports:export_notes",
    "exports:export_full_tracker",
]

WORKBOOK_EXPORT_ROUTE_NAMES = [
    "exports:export_applications",
    "exports:export_daily_logs",
    "exports:export_weekly_reviews",
    "exports:export_interviews",
    "exports:export_notes",
    "exports:export_full_tracker",
]

APPLICATION_CSV_HEADERS = [
    "application_id",
    "date_applied",
    "company_name",
    "job_title",
    "status",
    "source",
    "cv_version",
    "role_fit",
    "location",
    "work_type",
    "pipeline_stage",
    "response_date",
    "follow_up_status",
    "experience_level",
    "has_cv_version",
    "has_precise_source",
    "has_job_description",
    "has_required_skills",
    "has_follow_up_date",
    "is_analytics_ready",
]

DAILY_LOG_CSV_HEADERS = [
    "log_date",
    "target_applications",
    "actual_applications",
    "hours_spent",
]

PRIVATE_APPLICATION_FIELDS = [
    "job_description",
    "required_skills",
    "job_url",
    "contact_name",
    "contact_email",
    "notes",
]


class ExportViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aminul",
            password="StrongPass12345",
        )

    def test_authenticated_users_can_access_existing_export_routes(self):
        self.client.login(username="aminul", password="StrongPass12345")
        for route_name in EXPORT_ROUTE_NAMES:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)

    def test_workbook_exports_return_xlsx_responses(self):
        self.client.login(username="aminul", password="StrongPass12345")
        for route_name in WORKBOOK_EXPORT_ROUTE_NAMES:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response["Content-Type"], XLSX_CONTENT_TYPE)
                self.assertIn(".xlsx", response["Content-Disposition"])

    def test_export_routes_require_login(self):
        for route_name in EXPORT_ROUTE_NAMES:
            with self.subTest(route_name=route_name):
                response = self.client.get(reverse(route_name))
                self.assertEqual(response.status_code, 302)
                self.assertNotEqual(response["Location"], reverse(route_name))


class ExportServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="aminul",
            password="StrongPass12345",
        )

    def test_full_tracker_workbook_builds_bytes(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Example Ltd",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 9),
            status=ApplicationStatus.SUBMITTED,
        )
        DailyLog.objects.create(
            user=self.user,
            log_date=date(2026, 5, 9),
            target_applications=3,
            actual_applications=2,
        )
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=date(2026, 5, 10),
            target_applications=15,
            actual_applications=12,
        )
        Note.objects.create(
            user=self.user,
            title="CV decision",
            content="Use Data Analyst CV version for junior roles.",
        )
        file_bytes = build_full_tracker_workbook(self.user)
        self.assertIsInstance(file_bytes, bytes)
        self.assertGreater(len(file_bytes), 1000)


class DashboardCsvExportCommandTests(TestCase):
    def setUp(self):
        self.demo_user = User.objects.create_user(
            username="demo",
            password="DemoPass12345",
        )
        self.other_user = User.objects.create_user(
            username="private_user",
            password="StrongPass12345",
        )

    def _create_application(self, user, **kwargs):
        defaults = {
            "user": user,
            "company_name": "Demo Analytics Ltd",
            "job_title": "Data Analyst",
            "date_applied": date(2026, 5, 16),
            "status": ApplicationStatus.SUBMITTED,
            "source": ApplicationSource.LINKEDIN,
            "cv_version": "DA_CV_v2",
            "role_fit": RoleFit.STRONG,
            "location": "London / Remote UK",
            "work_type": WorkType.HYBRID,
            "pipeline_stage": PipelineStage.SUBMITTED,
            "response_date": None,
            "follow_up_status": FollowUpStatus.DUE,
            "experience_level": "junior / 0-2 years",
            "job_description": "Demo role summary for analytics completeness.",
            "required_skills": "SQL, Excel, dashboards",
            "follow_up_date": date(2026, 5, 20),
        }
        defaults.update(kwargs)
        return JobApplication.objects.create(**defaults)

    def _create_daily_log(self, user, **kwargs):
        defaults = {
            "user": user,
            "log_date": date(2026, 5, 16),
            "target_applications": 3,
            "actual_applications": 2,
            "hours_spent": "2.50",
        }
        defaults.update(kwargs)
        return DailyLog.objects.create(**defaults)

    def _run_command(self, output_dir):
        call_command("export_for_dashboards", output_dir=str(output_dir))

    def _read_csv(self, path):
        with Path(path).open(encoding="utf-8", newline="") as csv_file:
            return list(csv.reader(csv_file))

    def _read_csv_dicts(self, path):
        with Path(path).open(encoding="utf-8", newline="") as csv_file:
            return list(csv.DictReader(csv_file))

    def test_export_for_dashboards_creates_expected_csv_files(self):
        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            self.assertTrue((Path(temp_dir) / "applications.csv").exists())
            self.assertTrue((Path(temp_dir) / "daily_logs.csv").exists())

    def test_applications_csv_headers_are_exactly_correct(self):
        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            rows = self._read_csv(Path(temp_dir) / "applications.csv")
            self.assertEqual(rows[0], APPLICATION_CSV_HEADERS)

    def test_applications_csv_headers_exclude_private_fields(self):
        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            rows = self._read_csv(Path(temp_dir) / "applications.csv")
            for field in PRIVATE_APPLICATION_FIELDS:
                self.assertNotIn(field, rows[0])

    def test_daily_logs_csv_headers_are_exactly_correct(self):
        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            rows = self._read_csv(Path(temp_dir) / "daily_logs.csv")
            self.assertEqual(rows[0], DAILY_LOG_CSV_HEADERS)

    def test_exported_row_counts_match_known_demo_data(self):
        self._create_application(self.demo_user, company_name="Demo A")
        self._create_application(
            self.demo_user,
            company_name="Demo B",
            date_applied=date(2026, 5, 17),
        )
        self._create_daily_log(self.demo_user, log_date=date(2026, 5, 16))
        self._create_daily_log(self.demo_user, log_date=date(2026, 5, 17))

        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            application_rows = self._read_csv(Path(temp_dir) / "applications.csv")
            daily_log_rows = self._read_csv(Path(temp_dir) / "daily_logs.csv")
            self.assertEqual(len(application_rows) - 1, 2)
            self.assertEqual(len(daily_log_rows) - 1, 2)

    def test_command_exports_only_demo_user_records(self):
        self._create_application(self.demo_user, company_name="Demo Only")
        self._create_application(self.other_user, company_name="Private Company")
        self._create_daily_log(self.demo_user, log_date=date(2026, 5, 16))
        self._create_daily_log(self.other_user, log_date=date(2026, 5, 17))

        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            application_rows = self._read_csv(Path(temp_dir) / "applications.csv")
            daily_log_rows = self._read_csv(Path(temp_dir) / "daily_logs.csv")
            application_content = "\n".join(",".join(row) for row in application_rows)
            self.assertIn("Demo Only", application_content)
            self.assertNotIn("Private Company", application_content)
            self.assertEqual(len(application_rows) - 1, 1)
            self.assertEqual(len(daily_log_rows) - 1, 1)

    def test_complete_application_exports_yes_quality_flags(self):
        self._create_application(self.demo_user, company_name="Complete Demo")

        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            rows = self._read_csv_dicts(Path(temp_dir) / "applications.csv")
            row = rows[0]
            self.assertEqual(row["has_cv_version"], "yes")
            self.assertEqual(row["has_precise_source"], "yes")
            self.assertEqual(row["has_job_description"], "yes")
            self.assertEqual(row["has_required_skills"], "yes")
            self.assertEqual(row["has_follow_up_date"], "yes")
            self.assertEqual(row["is_analytics_ready"], "yes")

    def test_incomplete_application_exports_no_quality_flags(self):
        self._create_application(
            self.demo_user,
            company_name="Incomplete Demo",
            cv_version="",
            source=ApplicationSource.OTHER,
            job_description="",
            required_skills="",
            follow_up_date=None,
        )

        with TemporaryDirectory() as temp_dir:
            self._run_command(temp_dir)

            rows = self._read_csv_dicts(Path(temp_dir) / "applications.csv")
            row = rows[0]
            self.assertEqual(row["has_cv_version"], "no")
            self.assertEqual(row["has_precise_source"], "no")
            self.assertEqual(row["has_job_description"], "no")
            self.assertEqual(row["has_required_skills"], "no")
            self.assertEqual(row["has_follow_up_date"], "no")
            self.assertEqual(row["is_analytics_ready"], "no")

    def test_command_refuses_non_demo_usernames(self):
        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesMessage(
                CommandError,
                "Dashboard CSV export is demo-only and refuses non-demo users.",
            ):
                call_command(
                    "export_for_dashboards",
                    username="private_user",
                    output_dir=temp_dir,
                )
