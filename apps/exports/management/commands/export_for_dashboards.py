from __future__ import annotations

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog

APPLICATION_HEADERS = [
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
]

DAILY_LOG_HEADERS = [
    "log_date",
    "target_applications",
    "actual_applications",
    "hours_spent",
]


def csv_value(value):
    if value is None:
        return ""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class Command(BaseCommand):
    help = "Export synthetic demo data for dashboard tooling."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default="demo",
            help="Demo username to export. Only 'demo' is allowed.",
        )
        parser.add_argument(
            "--output-dir",
            default="dashboards/data",
            help="Directory where dashboard CSV files will be written.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        if username != "demo":
            raise CommandError(
                "Dashboard CSV export is demo-only and refuses non-demo users."
            )

        User = get_user_model()
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as exc:
            raise CommandError(
                "Demo user not found. Run 'python manage.py seed_demo_data' first."
            ) from exc

        output_dir = Path(options["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)

        applications_path = output_dir / "applications.csv"
        daily_logs_path = output_dir / "daily_logs.csv"

        self.export_applications(user, applications_path)
        self.export_daily_logs(user, daily_logs_path)

        self.stdout.write(self.style.SUCCESS(f"Exported {applications_path}"))
        self.stdout.write(self.style.SUCCESS(f"Exported {daily_logs_path}"))

    def export_applications(self, user, path: Path) -> None:
        applications = JobApplication.objects.filter(user=user).order_by(
            "date_applied", "id"
        )
        with path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(APPLICATION_HEADERS)
            for application in applications:
                writer.writerow(
                    [
                        application.id,
                        csv_value(application.date_applied),
                        application.company_name,
                        application.job_title,
                        application.status,
                        application.source,
                        application.cv_version,
                        application.role_fit,
                        application.location,
                        application.work_type,
                        application.pipeline_stage,
                        csv_value(application.response_date),
                        application.follow_up_status,
                        application.experience_level,
                    ]
                )

    def export_daily_logs(self, user, path: Path) -> None:
        daily_logs = DailyLog.objects.filter(user=user).order_by("log_date", "id")
        with path.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(DAILY_LOG_HEADERS)
            for log in daily_logs:
                writer.writerow(
                    [
                        csv_value(log.log_date),
                        log.target_applications,
                        log.actual_applications,
                        csv_value(log.hours_spent),
                    ]
                )
