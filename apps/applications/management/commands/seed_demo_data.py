from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

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
from apps.interviews.choices import InterviewOutcome, InterviewStage
from apps.interviews.models import InterviewPrep
from apps.notes.choices import NoteType
from apps.notes.models import Note
from apps.weekly_review.choices import FunnelDiagnosis, WeeklyMood
from apps.weekly_review.models import WeeklyReview


class Command(BaseCommand):
    help = "Seed CareerFunnel Tracker with realistic demo data."

    def handle(self, *args, **options):
        user = self.create_demo_user()
        self.clear_existing_demo_data(user)
        self.create_applications(user)
        self.create_daily_logs(user)
        self.create_weekly_reviews(user)
        self.create_notes(user)
        self.create_interview_preps(user)
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))
        self.stdout.write("Username: demo")
        self.stdout.write("Password: DemoPass12345")
        self.stdout.write("Open: http://127.0.0.1:8000/dashboard/")

    def create_demo_user(self):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username="demo",
            defaults={"email": "demo@example.com"},
        )
        if created:
            user.set_password("DemoPass12345")
            user.save()
        return user

    def clear_existing_demo_data(self, user):
        JobApplication.objects.filter(user=user).delete()
        DailyLog.objects.filter(user=user).delete()
        WeeklyReview.objects.filter(user=user).delete()
        Note.objects.filter(user=user).delete()
        InterviewPrep.objects.filter(user=user).delete()

    def create_applications(self, user):
        today = timezone.localdate()
        rows = [
            (
                "BrightData Analytics",
                "Junior Data Analyst",
                18,
                ApplicationStatus.ACKNOWLEDGED,
                14,
                RoleFit.STRONG,
            ),
            (
                "FinSight Group",
                "Reporting Analyst",
                16,
                ApplicationStatus.SCREENING_CALL,
                12,
                RoleFit.STRONG,
            ),
            (
                "Northbank Finance",
                "Data Analyst",
                15,
                ApplicationStatus.REJECTED,
                10,
                RoleFit.MEDIUM,
            ),
            (
                "Metro Insight Ltd",
                "BI Analyst",
                13,
                ApplicationStatus.NO_RESPONSE,
                None,
                RoleFit.MEDIUM,
            ),
            (
                "LedgerFlow",
                "Graduate Data Analyst",
                11,
                ApplicationStatus.INTERVIEW,
                7,
                RoleFit.STRONG,
            ),
            (
                "RetailOps Intelligence",
                "Operations Data Analyst",
                9,
                ApplicationStatus.ACKNOWLEDGED,
                6,
                RoleFit.STRONG,
            ),
            (
                "ClearPath BI",
                "Junior BI Reporting Analyst",
                7,
                ApplicationStatus.TECHNICAL_SCREEN,
                4,
                RoleFit.STRONG,
            ),
            (
                "DataBridge Solutions",
                "Data Analyst Intern",
                5,
                ApplicationStatus.SUBMITTED,
                None,
                RoleFit.STRONG,
            ),
            (
                "QuantOps Labs",
                "Junior Analytics Engineer",
                4,
                ApplicationStatus.AUTO_REJECTED,
                3,
                RoleFit.MEDIUM,
            ),
            (
                "InsightWorks UK",
                "Junior Insights Analyst",
                2,
                ApplicationStatus.SUBMITTED,
                None,
                RoleFit.STRONG,
            ),
            (
                "CoreLedger Analytics",
                "Finance Data Analyst",
                1,
                ApplicationStatus.SUBMITTED,
                None,
                RoleFit.STRONG,
            ),
        ]
        for company, title, days_ago, status, response_days_ago, fit in rows:
            cv_version = (
                "Finance_DA_CV_v1"
                if "Finance" in title or "Reporting" in title
                else "DA_CV_v2"
            )
            source = ApplicationSource.LINKEDIN
            required_skills = (
                "Python, SQL, Excel, reporting, dashboards, KPI analysis, "
                "stakeholder communication"
            )
            job_description = (
                f"Demo job description for {title}. The role involves "
                "reporting, analysis, data quality, dashboards, and "
                "business-facing insight."
            )
            follow_up_date = (
                today - timedelta(days=1)
                if response_days_ago is None
                else today + timedelta(days=3)
            )
            follow_up_status = (
                FollowUpStatus.DUE
                if response_days_ago is None
                else FollowUpStatus.NOT_DUE
            )

            if company == "Metro Insight Ltd":
                source = ApplicationSource.OTHER
            if company == "QuantOps Labs":
                cv_version = ""
            if company == "DataBridge Solutions":
                required_skills = ""
            if company == "InsightWorks UK":
                follow_up_date = None
                follow_up_status = FollowUpStatus.NOT_SET

            JobApplication.objects.create(
                user=user,
                company_name=company,
                job_title=title,
                job_url="https://example.com/jobs/demo",
                location="London / Remote UK",
                work_type=WorkType.HYBRID,
                salary_range="£28,000 - £38,000",
                source=source,
                role_fit=fit,
                date_applied=today - timedelta(days=days_ago),
                status=status,
                response_date=(
                    today - timedelta(days=response_days_ago)
                    if response_days_ago is not None
                    else None
                ),
                cv_version=cv_version,
                cover_letter_version="Tailored_CL_v1",
                experience_level=(
                    "junior / 0-2 years"
                    if "Junior" in title or "Graduate" in title or "Intern" in title
                    else "entry to mid-level"
                ),
                required_skills=required_skills,
                job_description=job_description,
                is_cv_tailored=fit == RoleFit.STRONG,
                is_cover_letter_tailored=fit == RoleFit.STRONG,
                portfolio_project_included=fit == RoleFit.STRONG,
                company_researched=response_days_ago is not None,
                follow_up_date=follow_up_date,
                follow_up_status=follow_up_status,
                pipeline_stage=(
                    PipelineStage.INTERVIEW
                    if status == ApplicationStatus.INTERVIEW
                    else PipelineStage.SUBMITTED
                ),
                next_action=(
                    "Prepare project walkthrough"
                    if status == ApplicationStatus.INTERVIEW
                    else "Monitor response or follow up when due"
                ),
                notes=(
                    "Demo application record for smart review, follow-ups, "
                    "dashboard, metrics, and export testing."
                ),
            )

    def create_daily_logs(self, user):
        today = timezone.localdate()
        actuals = [2, 3, 1, 3, 2, 0, 2, 3, 2, 1, 3, 2, 1]
        for index, actual in enumerate(actuals, start=1):
            DailyLog.objects.create(
                user=user,
                log_date=today - timedelta(days=14 - index),
                target_applications=3,
                actual_applications=actual,
                cover_letters_drafted=actual,
                responses_received=1 if index in [2, 4, 5, 7, 10] else 0,
                calls_received=1 if index in [4, 7] else 0,
                hours_spent=Decimal("2.50") if actual else Decimal("0.50"),
                energy_level=4 if actual >= 2 else 3,
                notes="Demo daily log entry.",
            )

    def create_weekly_reviews(self, user):
        today = timezone.localdate()
        week_one_ending = today - timedelta(days=7)
        WeeklyReview.objects.create(
            user=user,
            week_starting=week_one_ending - timedelta(days=6),
            week_ending=week_one_ending,
            target_applications=15,
            actual_applications=13,
            responses_received=3,
            screening_calls=1,
            technical_screens=0,
            interviews=0,
            offers=0,
            rejections=1,
            diagnosis=FunnelDiagnosis.SCREENING,
            mood=WeeklyMood.STEADY,
            what_worked="Junior data and finance-adjacent roles produced responses.",
            what_blocked="Too much browsing and over-editing.",
            lessons_learned="Targeting matters more than volume alone.",
            change_next_week="Submit earlier in the day.",
        )
        WeeklyReview.objects.create(
            user=user,
            week_starting=today - timedelta(days=6),
            week_ending=today,
            target_applications=15,
            actual_applications=10,
            responses_received=4,
            screening_calls=1,
            technical_screens=1,
            interviews=1,
            offers=0,
            rejections=1,
            diagnosis=FunnelDiagnosis.INTERVIEW,
            mood=WeeklyMood.MIXED,
            what_worked="Targeting improved.",
            what_blocked="Application volume dropped.",
            lessons_learned="Project explanation now matters more.",
            change_next_week=(
                "Prepare a 60-second profile answer and project walkthroughs."
            ),
        )

    def create_notes(self, user):
        today = timezone.localdate()
        notes = [
            (
                NoteType.STRATEGY,
                "Target junior data and reporting roles first",
                (
                    "Focus on Data Analyst, Reporting Analyst, BI Analyst, "
                    "and Insights Analyst roles."
                ),
                "strategy,targeting",
            ),
            (
                NoteType.CV_CHANGE,
                "Use finance/data positioning in CV headline",
                (
                    "Connect analytics projects with finance and operational "
                    "reporting background."
                ),
                "CV,finance",
            ),
            (
                NoteType.RECRUITER,
                "Recruiter asked for clearer SQL evidence",
                "Make SQL and database evidence more visible.",
                "recruiter,SQL",
            ),
            (
                NoteType.INTERVIEW,
                "Prepare project walkthroughs before interviews",
                "Explain projects as data products, not only websites.",
                "interview,projects",
            ),
            (
                NoteType.BLOCKER,
                "Over-searching reduces submissions",
                (
                    "Three good-enough roles submitted today is better than "
                    "ten perfect roles saved for later."
                ),
                "blocker,consistency",
            ),
        ]
        for note_type, title, content, tags in notes:
            Note.objects.create(
                user=user,
                note_type=note_type,
                title=title,
                content=content,
                tags=tags,
                decision_date=today,
                is_important=note_type != NoteType.BLOCKER,
            )


    def create_interview_preps(self, user):
        today = timezone.localdate()
        interview_apps = JobApplication.objects.filter(
            user=user,
            status__in=[
                ApplicationStatus.INTERVIEW,
                ApplicationStatus.SCREENING_CALL,
                ApplicationStatus.TECHNICAL_SCREEN,
            ],
        )
        for index, application in enumerate(interview_apps, start=1):
            InterviewPrep.objects.create(
                user=user,
                application=application,
                interview_date=today + timedelta(days=index + 1),
                stage=(
                    InterviewStage.FIRST
                    if application.status == ApplicationStatus.INTERVIEW
                    else InterviewStage.SCREENING
                ),
                outcome=InterviewOutcome.SCHEDULED,
                expected_topics=(
                    "60-second profile, Python/Excel/SQL evidence, project "
                    "walkthrough, business scenario questions."
                ),
                projects_to_mention=(
                    "BakeOps Intelligence, MarketVista Dashboard, RiskWise "
                    "Planner, CareerFunnel Tracker"
                ),
                questions_to_prepare=(
                    "Why this role? Why this company? Explain one analytics "
                    "project. How do you handle messy data?"
                ),
                profile_answer_prepared=index == 1,
                company_answer_prepared=index == 1,
                project_walkthrough_prepared=False,
                sql_practice_done=False,
                python_practice_done=False,
                star_examples_prepared=False,
                questions_for_employer_prepared=False,
                reflection="Demo interview preparation record.",
            )
