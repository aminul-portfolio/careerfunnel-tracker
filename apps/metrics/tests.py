from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import ApplicationSource, ApplicationStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog

from .services import (
    build_application_quality_report,
    build_cv_version_performance,
    build_data_quality_report,
    build_funnel_metrics,
    build_rejection_pattern_report,
    build_source_roi,
    diagnose_funnel,
    safe_percentage,
)


class MetricsServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_safe_percentage_returns_zero_when_denominator_is_zero(self):
        self.assertEqual(safe_percentage(5, 0), 0.0)

    def test_safe_percentage_calculates_correctly(self):
        self.assertEqual(safe_percentage(2, 10), 20.0)

    def test_metrics_without_data_returns_zero_values(self):
        metrics = build_funnel_metrics(self.user)
        self.assertEqual(metrics.total_applications, 0)
        self.assertEqual(metrics.response_rate, 0.0)

    def test_metrics_calculates_application_counts(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Company A",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
            status=ApplicationStatus.SUBMITTED,
        )
        JobApplication.objects.create(
            user=self.user,
            company_name="Company B",
            job_title="BI Analyst",
            date_applied=date(2026, 5, 2),
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        JobApplication.objects.create(
            user=self.user,
            company_name="Company C",
            job_title="Reporting Analyst",
            date_applied=date(2026, 5, 3),
            status=ApplicationStatus.INTERVIEW,
        )
        metrics = build_funnel_metrics(self.user)
        self.assertEqual(metrics.total_applications, 3)
        self.assertEqual(metrics.response_count, 2)
        self.assertEqual(metrics.response_rate, 66.67)

    def test_metrics_calculates_daily_log_totals(self):
        DailyLog.objects.create(
            user=self.user,
            log_date=date(2026, 5, 9),
            target_applications=3,
            actual_applications=2,
            hours_spent=Decimal("2.50"),
            energy_level=4,
        )
        DailyLog.objects.create(
            user=self.user,
            log_date=date(2026, 5, 10),
            target_applications=3,
            actual_applications=3,
            hours_spent=Decimal("3.00"),
            energy_level=4,
        )
        metrics = build_funnel_metrics(self.user)
        self.assertEqual(metrics.daily_target_total, 6)
        self.assertEqual(metrics.daily_actual_total, 5)
        self.assertEqual(metrics.daily_target_hit_rate, 50.0)

    def test_diagnosis_without_applications(self):
        diagnosis = diagnose_funnel(build_funnel_metrics(self.user))
        self.assertEqual(diagnosis.diagnosis_label, "Unknown / not enough data")


class SourceROIAnalyticsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="roi_user", password="StrongPass12345")

    def _create_app(self, **kwargs):
        defaults = {
            "user": self.user,
            "company_name": "Acme",
            "job_title": "Analyst",
            "date_applied": date(2026, 5, 1),
            "status": ApplicationStatus.SUBMITTED,
            "source": ApplicationSource.OTHER,
        }
        defaults.update(kwargs)
        return JobApplication.objects.create(**defaults)

    def test_build_source_roi_empty_returns_empty_list(self):
        self.assertEqual(build_source_roi(self.user), [])

    def test_build_source_roi_groups_by_source(self):
        self._create_app(source=ApplicationSource.LINKEDIN, company_name="A")
        self._create_app(source=ApplicationSource.LINKEDIN, company_name="B")
        self._create_app(source=ApplicationSource.INDEED, company_name="C")
        rows = build_source_roi(self.user)
        self.assertEqual(len(rows), 2)
        by_source = {r.source: r for r in rows}
        self.assertEqual(by_source[ApplicationSource.LINKEDIN].total_applications, 2)
        self.assertEqual(by_source[ApplicationSource.LINKEDIN].source_label, "LinkedIn")
        self.assertEqual(by_source[ApplicationSource.INDEED].total_applications, 1)
        self.assertEqual(by_source[ApplicationSource.INDEED].source_label, "Indeed")

    def test_build_source_roi_response_rate(self):
        self._create_app(
            source=ApplicationSource.REED,
            company_name="C1",
            status=ApplicationStatus.SUBMITTED,
        )
        self._create_app(
            source=ApplicationSource.REED,
            company_name="C2",
            status=ApplicationStatus.SUBMITTED,
        )
        self._create_app(
            source=ApplicationSource.REED,
            company_name="C3",
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self._create_app(
            source=ApplicationSource.REED,
            company_name="C4",
            status=ApplicationStatus.AUTO_REJECTED,
        )
        rows = build_source_roi(self.user)
        reed = next(r for r in rows if r.source == ApplicationSource.REED)
        self.assertEqual(reed.responses, 2)
        self.assertEqual(reed.total_applications, 4)
        self.assertEqual(reed.response_rate, 50.0)

    def test_build_source_roi_interview_rate_counts_interview_and_offer(self):
        self._create_app(
            source=ApplicationSource.GLASSDOOR,
            company_name="G1",
            status=ApplicationStatus.SUBMITTED,
        )
        self._create_app(
            source=ApplicationSource.GLASSDOOR,
            company_name="G2",
            status=ApplicationStatus.INTERVIEW,
        )
        self._create_app(
            source=ApplicationSource.GLASSDOOR,
            company_name="G3",
            status=ApplicationStatus.INTERVIEW,
        )
        self._create_app(
            source=ApplicationSource.GLASSDOOR,
            company_name="G4",
            status=ApplicationStatus.OFFER,
        )
        self._create_app(
            source=ApplicationSource.GLASSDOOR,
            company_name="G5",
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        rows = build_source_roi(self.user)
        g = next(r for r in rows if r.source == ApplicationSource.GLASSDOOR)
        self.assertEqual(g.interviews, 3)
        self.assertEqual(g.total_applications, 5)
        self.assertEqual(g.interview_rate, 60.0)

    def test_build_source_roi_offer_rate(self):
        self._create_app(
            source=ApplicationSource.REFERRAL,
            company_name="R1",
            status=ApplicationStatus.OFFER,
        )
        self._create_app(
            source=ApplicationSource.REFERRAL,
            company_name="R2",
            status=ApplicationStatus.INTERVIEW,
        )
        self._create_app(
            source=ApplicationSource.REFERRAL,
            company_name="R3",
            status=ApplicationStatus.SUBMITTED,
        )
        self._create_app(
            source=ApplicationSource.REFERRAL,
            company_name="R4",
            status=ApplicationStatus.SUBMITTED,
        )
        rows = build_source_roi(self.user)
        ref = next(r for r in rows if r.source == ApplicationSource.REFERRAL)
        self.assertEqual(ref.offers, 1)
        self.assertEqual(ref.offer_rate, 25.0)

    def test_build_source_roi_blank_source_normalizes_to_other_bucket(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="BlankCo",
            job_title="Role",
            date_applied=date(2026, 5, 2),
            status=ApplicationStatus.SUBMITTED,
            source="",
        )
        self._create_app(source=ApplicationSource.OTHER, company_name="OtherCo")
        rows = build_source_roi(self.user)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row.source, ApplicationSource.OTHER)
        self.assertEqual(row.total_applications, 2)

    def test_build_source_roi_sorts_by_response_then_interview_then_volume(self):
        self._create_app(
            source=ApplicationSource.LINKEDIN,
            company_name="L1",
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self._create_app(
            source=ApplicationSource.LINKEDIN,
            company_name="L2",
            status=ApplicationStatus.ACKNOWLEDGED,
        )
        self._create_app(
            source=ApplicationSource.INDEED, company_name="I1", status=ApplicationStatus.SUBMITTED
        )
        self._create_app(
            source=ApplicationSource.INDEED, company_name="I2", status=ApplicationStatus.SUBMITTED
        )
        self._create_app(
            source=ApplicationSource.INDEED, company_name="I3", status=ApplicationStatus.SUBMITTED
        )
        self._create_app(
            source=ApplicationSource.INDEED, company_name="I4", status=ApplicationStatus.SUBMITTED
        )
        rows = build_source_roi(self.user)
        self.assertEqual(
            [r.source for r in rows], [ApplicationSource.LINKEDIN, ApplicationSource.INDEED]
        )


class CVVersionPerformanceAnalyticsTests(TestCase):
    """Tests for CV Version Performance analytics (service-level grouping and rates)."""

    def setUp(self):
        self.user = User.objects.create_user(username="cv_perf_user", password="StrongPass12345")

    def _create_app(self, **kwargs):
        defaults = {
            "user": self.user,
            "company_name": "Acme",
            "job_title": "Analyst",
            "date_applied": date(2026, 5, 1),
            "status": ApplicationStatus.SUBMITTED,
            "source": ApplicationSource.OTHER,
            "cv_version": "v1",
        }
        defaults.update(kwargs)
        return JobApplication.objects.create(**defaults)

    def test_build_cv_version_performance_empty_returns_empty_list(self):
        self.assertEqual(build_cv_version_performance(self.user), [])

    def test_build_cv_version_performance_groups_by_cv_version(self):
        self._create_app(cv_version="Analytics CV", company_name="A1")
        self._create_app(cv_version="Analytics CV", company_name="A2")
        self._create_app(cv_version="Generalist CV", company_name="B1")
        rows = build_cv_version_performance(self.user)
        self.assertEqual(len(rows), 2)
        by_cv = {r.cv_version: r for r in rows}
        self.assertEqual(by_cv["Analytics CV"].total_applications, 2)
        self.assertEqual(by_cv["Generalist CV"].total_applications, 1)

    def test_build_cv_version_performance_blank_cv_version_is_unspecified(self):
        self._create_app(cv_version="", company_name="Blank1")
        self._create_app(cv_version="   ", company_name="Spaces")
        self._create_app(cv_version="Named", company_name="NamedCo")
        rows = build_cv_version_performance(self.user)
        by_cv = {r.cv_version: r for r in rows}
        self.assertIn("Unspecified", by_cv)
        self.assertEqual(by_cv["Unspecified"].total_applications, 2)
        self.assertEqual(by_cv["Named"].total_applications, 1)

    def test_build_cv_version_performance_response_rate(self):
        self._create_app(
            cv_version="v-test",
            company_name="C1",
            status=ApplicationStatus.SUBMITTED,
        )
        self._create_app(
            cv_version="v-test",
            company_name="C2",
            status=ApplicationStatus.SUBMITTED,
        )
        self._create_app(
            cv_version="v-test", company_name="C3", status=ApplicationStatus.ACKNOWLEDGED
        )
        self._create_app(
            cv_version="v-test", company_name="C4", status=ApplicationStatus.AUTO_REJECTED
        )
        rows = build_cv_version_performance(self.user)
        row = next(r for r in rows if r.cv_version == "v-test")
        self.assertEqual(row.responses, 2)
        self.assertEqual(row.total_applications, 4)
        self.assertEqual(row.response_rate, 50.0)

    def test_build_cv_version_performance_interview_rate(self):
        self._create_app(cv_version="v-int", company_name="G1", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="v-int", company_name="G2", status=ApplicationStatus.INTERVIEW)
        self._create_app(cv_version="v-int", company_name="G3", status=ApplicationStatus.INTERVIEW)
        self._create_app(cv_version="v-int", company_name="G4", status=ApplicationStatus.OFFER)
        self._create_app(
            cv_version="v-int", company_name="G5", status=ApplicationStatus.ACKNOWLEDGED
        )
        rows = build_cv_version_performance(self.user)
        row = next(r for r in rows if r.cv_version == "v-int")
        self.assertEqual(row.interviews, 3)
        self.assertEqual(row.total_applications, 5)
        self.assertEqual(row.interview_rate, 60.0)

    def test_build_cv_version_performance_offer_rate(self):
        self._create_app(cv_version="v-off", company_name="R1", status=ApplicationStatus.OFFER)
        self._create_app(cv_version="v-off", company_name="R2", status=ApplicationStatus.INTERVIEW)
        self._create_app(cv_version="v-off", company_name="R3", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="v-off", company_name="R4", status=ApplicationStatus.SUBMITTED)
        rows = build_cv_version_performance(self.user)
        row = next(r for r in rows if r.cv_version == "v-off")
        self.assertEqual(row.offers, 1)
        self.assertEqual(row.offer_rate, 25.0)

    def test_build_cv_version_performance_rejection_rate(self):
        self._create_app(cv_version="v-rej", company_name="J1", status=ApplicationStatus.REJECTED)
        self._create_app(
            cv_version="v-rej", company_name="J2", status=ApplicationStatus.AUTO_REJECTED
        )
        self._create_app(cv_version="v-rej", company_name="J3", status=ApplicationStatus.SUBMITTED)
        self._create_app(
            cv_version="v-rej", company_name="J4", status=ApplicationStatus.ACKNOWLEDGED
        )
        rows = build_cv_version_performance(self.user)
        row = next(r for r in rows if r.cv_version == "v-rej")
        self.assertEqual(row.rejections, 2)
        self.assertEqual(row.total_applications, 4)
        self.assertEqual(row.rejection_rate, 50.0)

    def test_build_cv_version_performance_sorts_by_response_then_interview_then_volume(self):
        self._create_app(
            cv_version="high-response", company_name="H1", status=ApplicationStatus.ACKNOWLEDGED
        )
        self._create_app(
            cv_version="high-response", company_name="H2", status=ApplicationStatus.ACKNOWLEDGED
        )
        self._create_app(
            cv_version="low-response", company_name="L1", status=ApplicationStatus.SUBMITTED
        )
        self._create_app(
            cv_version="low-response", company_name="L2", status=ApplicationStatus.SUBMITTED
        )
        self._create_app(
            cv_version="low-response", company_name="L3", status=ApplicationStatus.SUBMITTED
        )
        self._create_app(
            cv_version="low-response", company_name="L4", status=ApplicationStatus.SUBMITTED
        )
        rows = build_cv_version_performance(self.user)
        self.assertEqual([r.cv_version for r in rows], ["high-response", "low-response"])


class RejectionPatternReportTests(TestCase):
    """Tests for rejection pattern analytics (Sprint 2B Task 1)."""

    _LOW_SAMPLE_WARNING = (
        "Not enough applications yet for strong pattern conclusions. "
        "Treat this as directional only."
    )

    def setUp(self):
        self.user = User.objects.create_user(
            username="rej_pattern_user", password="StrongPass12345"
        )

    def _create_app(self, **kwargs):
        defaults = {
            "user": self.user,
            "company_name": "Acme",
            "job_title": "Analyst",
            "date_applied": date(2026, 5, 1),
            "status": ApplicationStatus.SUBMITTED,
            "source": ApplicationSource.OTHER,
            "cv_version": "v1",
        }
        defaults.update(kwargs)
        return JobApplication.objects.create(**defaults)

    def test_empty_data_returns_sensible_report(self):
        report = build_rejection_pattern_report(self.user)
        self.assertEqual(report.total_applications, 0)
        self.assertEqual(report.total_rejections, 0)
        self.assertEqual(report.auto_rejections, 0)
        self.assertEqual(report.rejection_rate, 0.0)
        self.assertEqual(report.auto_rejection_rate, 0.0)
        self.assertFalse(report.has_enough_data)
        self.assertEqual(report.sample_warning, self._LOW_SAMPLE_WARNING)
        self.assertEqual(report.by_source, ())
        self.assertEqual(report.by_cv_version, ())
        self.assertEqual(report.seniority_risk_count, 0)
        self.assertTrue(len(report.recommendations) >= 1)
        self.assertIn("Log job applications", report.recommendations[0])

    def test_low_sample_size_warning_under_twenty_applications(self):
        for i in range(5):
            self._create_app(company_name=f"C{i}", status=ApplicationStatus.SUBMITTED)
        report = build_rejection_pattern_report(self.user)
        self.assertFalse(report.has_enough_data)
        self.assertEqual(report.sample_warning, self._LOW_SAMPLE_WARNING)

    def test_has_enough_data_when_twenty_or_more_applications(self):
        for i in range(20):
            self._create_app(company_name=f"Co{i}", status=ApplicationStatus.SUBMITTED)
        report = build_rejection_pattern_report(self.user)
        self.assertTrue(report.has_enough_data)
        self.assertEqual(report.sample_warning, "")

    def test_total_rejection_counts_and_rates(self):
        self._create_app(company_name="A", status=ApplicationStatus.REJECTED)
        self._create_app(company_name="B", status=ApplicationStatus.AUTO_REJECTED)
        self._create_app(company_name="C", status=ApplicationStatus.ACKNOWLEDGED)
        self._create_app(company_name="D", status=ApplicationStatus.SUBMITTED)
        report = build_rejection_pattern_report(self.user)
        self.assertEqual(report.total_applications, 4)
        self.assertEqual(report.total_rejections, 2)
        self.assertEqual(report.rejection_rate, 50.0)

    def test_auto_rejection_count_and_rate(self):
        self._create_app(company_name="X1", status=ApplicationStatus.AUTO_REJECTED)
        self._create_app(company_name="X2", status=ApplicationStatus.AUTO_REJECTED)
        self._create_app(company_name="X3", status=ApplicationStatus.REJECTED)
        self._create_app(company_name="X4", status=ApplicationStatus.INTERVIEW)
        report = build_rejection_pattern_report(self.user)
        self.assertEqual(report.auto_rejections, 2)
        self.assertEqual(report.auto_rejection_rate, 50.0)

    def test_rejections_grouped_by_source(self):
        self._create_app(
            source=ApplicationSource.LINKEDIN,
            company_name="L1",
            status=ApplicationStatus.REJECTED,
        )
        self._create_app(
            source=ApplicationSource.LINKEDIN,
            company_name="L2",
            status=ApplicationStatus.REJECTED,
        )
        self._create_app(
            source=ApplicationSource.INDEED,
            company_name="I1",
            status=ApplicationStatus.AUTO_REJECTED,
        )
        self._create_app(
            source=ApplicationSource.INDEED,
            company_name="I2",
            status=ApplicationStatus.SUBMITTED,
        )
        report = build_rejection_pattern_report(self.user)
        by_src = {r.source: r for r in report.by_source}
        self.assertEqual(by_src[ApplicationSource.LINKEDIN].rejection_count, 2)
        self.assertEqual(by_src[ApplicationSource.LINKEDIN].total_applications, 2)
        self.assertEqual(by_src[ApplicationSource.LINKEDIN].rejection_rate, 100.0)
        self.assertEqual(by_src[ApplicationSource.INDEED].rejection_count, 1)
        self.assertEqual(by_src[ApplicationSource.INDEED].total_applications, 2)
        self.assertEqual(by_src[ApplicationSource.INDEED].rejection_rate, 50.0)

    def test_rejections_grouped_by_cv_version(self):
        self._create_app(
            cv_version="vA", company_name="A1", status=ApplicationStatus.REJECTED
        )
        self._create_app(
            cv_version="vA", company_name="A2", status=ApplicationStatus.SUBMITTED
        )
        self._create_app(
            cv_version="vB",
            company_name="B1",
            status=ApplicationStatus.AUTO_REJECTED,
        )
        report = build_rejection_pattern_report(self.user)
        by_cv = {r.cv_version: r for r in report.by_cv_version}
        self.assertEqual(by_cv["vA"].rejection_count, 1)
        self.assertEqual(by_cv["vA"].total_applications, 2)
        self.assertEqual(by_cv["vA"].rejection_rate, 50.0)
        self.assertEqual(by_cv["vB"].rejection_count, 1)
        self.assertEqual(by_cv["vB"].rejection_rate, 100.0)

    def test_blank_cv_version_normalized_to_unspecified(self):
        self._create_app(cv_version="", company_name="U1", status=ApplicationStatus.REJECTED)
        self._create_app(
            cv_version="   ", company_name="U2", status=ApplicationStatus.AUTO_REJECTED
        )
        report = build_rejection_pattern_report(self.user)
        by_cv = {r.cv_version: r for r in report.by_cv_version}
        self.assertIn("Unspecified", by_cv)
        self.assertEqual(by_cv["Unspecified"].rejection_count, 2)

    def test_seniority_risk_detects_signals_in_rejected_applications_only(self):
        self._create_app(
            company_name="S1",
            job_title="Senior Data Analyst",
            status=ApplicationStatus.REJECTED,
        )
        self._create_app(
            company_name="S2",
            job_title="Junior Analyst",
            required_skills="Minimum 5 years SQL",
            status=ApplicationStatus.AUTO_REJECTED,
        )
        self._create_app(
            company_name="S3",
            job_title="Intern",
            job_description="Looking for head of analytics",
            status=ApplicationStatus.REJECTED,
        )
        self._create_app(
            company_name="S4",
            job_title="Senior Analyst",
            status=ApplicationStatus.INTERVIEW,
        )
        report = build_rejection_pattern_report(self.user)
        self.assertEqual(report.seniority_risk_count, 3)

    def test_recommendations_non_empty_with_data(self):
        self._create_app(company_name="R1", status=ApplicationStatus.SUBMITTED)
        report = build_rejection_pattern_report(self.user)
        self.assertTrue(report.recommendations)

    def test_recommendations_include_seniority_guidance_when_risk_present(self):
        self._create_app(
            company_name="SrCo",
            job_title="Senior Analyst",
            status=ApplicationStatus.REJECTED,
        )
        report = build_rejection_pattern_report(self.user)
        joined = " ".join(report.recommendations)
        self.assertIn("senior", joined.lower())


class ApplicationQualityReportTests(TestCase):
    """Sprint 3A Task 1: application completeness and stretch-role signals."""

    _JD_40 = "x" * 40
    _SKILLS_10 = "y" * 10

    def setUp(self):
        self.user = User.objects.create_user(username="quality_user", password="StrongPass12345")

    def _clean_defaults(self):
        return {
            "user": self.user,
            "company_name": "Acme Corp",
            "job_title": "Data Analyst",
            "date_applied": date(2026, 5, 1),
            "status": ApplicationStatus.SUBMITTED,
            "source": ApplicationSource.LINKEDIN,
            "cv_version": "v1",
            "job_description": self._JD_40,
            "required_skills": self._SKILLS_10,
            "follow_up_date": date(2026, 5, 10),
        }

    def _create_app(self, **kwargs):
        d = self._clean_defaults()
        d.update(kwargs)
        return JobApplication.objects.create(**d)

    def test_empty_data_returns_sensible_report(self):
        report = build_application_quality_report(self.user)
        self.assertEqual(report.total_applications, 0)
        self.assertEqual(report.applications_with_issues, 0)
        self.assertEqual(report.quality_issue_rate, 0.0)
        self.assertEqual(report.missing_cv_version_count, 0)
        self.assertEqual(report.missing_source_count, 0)
        self.assertEqual(report.missing_job_description_count, 0)
        self.assertEqual(report.missing_required_skills_count, 0)
        self.assertEqual(report.missing_follow_up_count, 0)
        self.assertEqual(report.seniority_risk_count, 0)
        self.assertEqual(report.issue_rows, ())
        self.assertEqual(len(report.recommendations), 1)
        self.assertIn("Log job applications", report.recommendations[0])

    def test_clean_applications_return_zero_issues(self):
        self._create_app(company_name="CoA")
        self._create_app(company_name="CoB", date_applied=date(2026, 5, 2))
        report = build_application_quality_report(self.user)
        self.assertEqual(report.total_applications, 2)
        self.assertEqual(report.applications_with_issues, 0)
        self.assertEqual(report.quality_issue_rate, 0.0)
        self.assertEqual(report.issue_rows, ())
        self.assertEqual(len(report.recommendations), 1)
        self.assertIn("continue logging", report.recommendations[0].lower())

    def test_missing_cv_version_detected(self):
        self._create_app(company_name="NoCv", cv_version="")
        self._create_app(company_name="SpacesCv", cv_version="   ")
        report = build_application_quality_report(self.user)
        self.assertEqual(report.missing_cv_version_count, 2)
        self.assertEqual(report.applications_with_issues, 2)
        rows = {r.company_name: r for r in report.issue_rows}
        self.assertIn("Missing CV version", rows["NoCv"].issues)
        self.assertEqual(rows["NoCv"].issue_count, 1)

    def test_missing_or_other_source_detected(self):
        self._create_app(company_name="BlankSrc", source="")
        self._create_app(company_name="OtherSrc", source=ApplicationSource.OTHER)
        self._create_app(company_name="SpacesSrc", source="   ")
        report = build_application_quality_report(self.user)
        self.assertEqual(report.missing_source_count, 3)
        for name in ("BlankSrc", "OtherSrc", "SpacesSrc"):
            row = next(r for r in report.issue_rows if r.company_name == name)
            self.assertIn("Missing precise source", row.issues)

    def test_thin_job_description_detected(self):
        self._create_app(company_name="Thin", job_description="x" * 39)
        self._create_app(company_name="Empty", job_description="")
        self._create_app(company_name="Spaces", job_description="   ")
        report = build_application_quality_report(self.user)
        self.assertEqual(report.missing_job_description_count, 3)
        for cn in ("Thin", "Empty", "Spaces"):
            row = next(r for r in report.issue_rows if r.company_name == cn)
            self.assertIn("Missing or thin job description", row.issues)

    def test_missing_required_skills_detected(self):
        self._create_app(company_name="ShortSkills", required_skills="y" * 9)
        self._create_app(company_name="NoSkills", required_skills="")
        report = build_application_quality_report(self.user)
        self.assertEqual(report.missing_required_skills_count, 2)
        for cn in ("ShortSkills", "NoSkills"):
            row = next(r for r in report.issue_rows if r.company_name == cn)
            self.assertIn("Missing required skills", row.issues)

    def test_missing_follow_up_only_for_active_pipeline_statuses(self):
        self._create_app(
            company_name="SubNoFu",
            status=ApplicationStatus.SUBMITTED,
            follow_up_date=None,
        )
        self._create_app(
            company_name="AckNoFu",
            status=ApplicationStatus.ACKNOWLEDGED,
            follow_up_date=None,
        )
        self._create_app(
            company_name="ScreenNoFu",
            status=ApplicationStatus.SCREENING_CALL,
            follow_up_date=None,
        )
        self._create_app(
            company_name="TechNoFu",
            status=ApplicationStatus.TECHNICAL_SCREEN,
            follow_up_date=None,
        )
        self._create_app(
            company_name="IntNoFu",
            status=ApplicationStatus.INTERVIEW,
            follow_up_date=None,
        )
        report = build_application_quality_report(self.user)
        self.assertEqual(report.missing_follow_up_count, 5)
        for cn in (
            "SubNoFu",
            "AckNoFu",
            "ScreenNoFu",
            "TechNoFu",
            "IntNoFu",
        ):
            row = next(r for r in report.issue_rows if r.company_name == cn)
            self.assertIn("Missing follow-up date", row.issues)

    def test_missing_follow_up_not_flagged_for_offer_rejected_auto_rejected(self):
        self._create_app(
            company_name="OfferNoFu",
            status=ApplicationStatus.OFFER,
            follow_up_date=None,
        )
        self._create_app(
            company_name="RejNoFu",
            status=ApplicationStatus.REJECTED,
            follow_up_date=None,
        )
        self._create_app(
            company_name="AutoRejNoFu",
            status=ApplicationStatus.AUTO_REJECTED,
            follow_up_date=None,
        )
        self._create_app(
            company_name="NoRespNoFu",
            status=ApplicationStatus.NO_RESPONSE,
            follow_up_date=None,
        )
        report = build_application_quality_report(self.user)
        self.assertEqual(report.missing_follow_up_count, 0)
        self.assertEqual(report.applications_with_issues, 0)
        self.assertEqual(report.issue_rows, ())

    def test_seniority_stretch_role_risk_detected(self):
        self._create_app(
            company_name="SeniorTitle",
            job_title="Senior Data Analyst",
        )
        self._create_app(
            company_name="SkillsSig",
            job_title="Analyst",
            required_skills="We need minimum 5 years of SQL experience.",
        )
        self._create_app(
            company_name="JdSig",
            job_title="Analyst",
            job_description=self._JD_40 + " Head of department collaboration.",
        )
        report = build_application_quality_report(self.user)
        self.assertEqual(report.seniority_risk_count, 3)
        for cn in ("SeniorTitle", "SkillsSig", "JdSig"):
            row = next(r for r in report.issue_rows if r.company_name == cn)
            self.assertIn("Seniority or stretch-role risk", row.issues)

    def test_issue_rows_issue_count_matches_issues_len(self):
        self._create_app(
            company_name="Multi",
            cv_version="",
            source=ApplicationSource.OTHER,
            job_description="",
            required_skills="",
            follow_up_date=None,
            status=ApplicationStatus.SUBMITTED,
            job_title="Lead Engineer",
        )
        report = build_application_quality_report(self.user)
        self.assertEqual(len(report.issue_rows), 1)
        row = report.issue_rows[0]
        self.assertEqual(row.issue_count, len(row.issues))
        self.assertGreaterEqual(row.issue_count, 5)

    def test_recommendations_returned_when_issues_exist(self):
        self._create_app(company_name="Bad", cv_version="", source=ApplicationSource.OTHER)
        report = build_application_quality_report(self.user)
        self.assertGreaterEqual(len(report.recommendations), 1)
        joined = " ".join(report.recommendations).lower()
        self.assertIn("cv", joined)
        self.assertIn("source", joined)

    def test_issue_rows_sorted_by_count_date_company(self):
        self._create_app(
            company_name="Beta",
            date_applied=date(2026, 5, 1),
            cv_version="",
            source=ApplicationSource.LINKEDIN,
        )
        self._create_app(
            company_name="Alpha",
            date_applied=date(2026, 5, 10),
            cv_version="",
            source=ApplicationSource.LINKEDIN,
        )
        self._create_app(
            company_name="Gamma",
            date_applied=date(2026, 5, 15),
            cv_version="",
            source=ApplicationSource.LINKEDIN,
            job_description="",
        )
        report = build_application_quality_report(self.user)
        names = [r.company_name for r in report.issue_rows]
        self.assertEqual(names[0], "Gamma")
        self.assertEqual(set(names[1:]), {"Alpha", "Beta"})
        self.assertLess(names.index("Alpha"), names.index("Beta"))


class DataQualityReportTests(TestCase):
    """Sprint 4A: aggregate data quality for analytics governance."""

    _JD_40 = "x" * 40
    _SKILLS_10 = "y" * 10

    def setUp(self):
        self.user = User.objects.create_user(username="dq_user", password="StrongPass12345")

    def _clean_defaults(self):
        return {
            "user": self.user,
            "company_name": "Acme Corp",
            "job_title": "Data Analyst",
            "date_applied": date(2026, 5, 1),
            "status": ApplicationStatus.SUBMITTED,
            "source": ApplicationSource.LINKEDIN,
            "cv_version": "v1",
            "job_description": self._JD_40,
            "required_skills": self._SKILLS_10,
            "follow_up_date": date(2026, 5, 10),
        }

    def _create_app(self, **kwargs):
        d = self._clean_defaults()
        d.update(kwargs)
        return JobApplication.objects.create(**d)

    def test_empty_data_returns_sensible_report(self):
        report = build_data_quality_report(self.user)
        self.assertEqual(report.total_applications, 0)
        self.assertEqual(report.analytics_ready_applications, 0)
        self.assertEqual(report.analytics_ready_rate, 0.0)
        self.assertEqual(report.data_quality_score, 0.0)
        self.assertEqual(report.missing_source_count, 0)
        self.assertEqual(report.missing_cv_version_count, 0)
        self.assertEqual(report.missing_job_description_count, 0)
        self.assertEqual(report.missing_required_skills_count, 0)
        self.assertEqual(report.missing_follow_up_count, 0)
        self.assertEqual(report.generic_source_count, 0)
        for c in report.checks:
            self.assertEqual(c.issue_count, 0)
            self.assertEqual(c.severity, "success")
        self.assertEqual(len(report.recommendations), 1)
        self.assertIn("Log job applications", report.recommendations[0])

    def test_clean_applications_produce_full_data_quality_score(self):
        self._create_app(company_name="CoA")
        self._create_app(company_name="CoB", date_applied=date(2026, 5, 2))
        report = build_data_quality_report(self.user)
        self.assertEqual(report.total_applications, 2)
        self.assertEqual(report.analytics_ready_applications, 2)
        self.assertEqual(report.analytics_ready_rate, 100.0)
        self.assertEqual(report.data_quality_score, 100.0)
        self.assertEqual(report.missing_source_count, 0)
        self.assertTrue(any("continue logging" in r.lower() for r in report.recommendations))

    def test_missing_source_is_counted(self):
        self._create_app(company_name="BlankSrc", source="")
        self._create_app(company_name="SpacesSrc", source="   ")
        report = build_data_quality_report(self.user)
        self.assertEqual(report.missing_source_count, 2)
        self.assertEqual(report.generic_source_count, 0)
        self.assertEqual(report.analytics_ready_applications, 0)
        precise = next(c for c in report.checks if c.check_name == "Precise application source")
        self.assertEqual(precise.issue_count, 2)
        self.assertEqual(precise.severity, "danger")

    def test_generic_other_source_is_counted(self):
        self._create_app(company_name="OtherOnly", source=ApplicationSource.OTHER)
        report = build_data_quality_report(self.user)
        self.assertEqual(report.generic_source_count, 1)
        self.assertEqual(report.missing_source_count, 1)
        generic_chk = next(c for c in report.checks if "generic" in c.check_name.lower())
        self.assertEqual(generic_chk.issue_count, 1)
        self.assertEqual(generic_chk.severity, "danger")

    def test_missing_cv_version_is_counted(self):
        self._create_app(company_name="NoCv", cv_version="")
        self._create_app(company_name="SpaceCv", cv_version="   ")
        report = build_data_quality_report(self.user)
        self.assertEqual(report.missing_cv_version_count, 2)
        cv_chk = next(c for c in report.checks if "CV version" in c.check_name)
        self.assertEqual(cv_chk.issue_count, 2)

    def test_thin_job_description_is_counted(self):
        self._create_app(company_name="Thin", job_description="x" * 39)
        report = build_data_quality_report(self.user)
        self.assertEqual(report.missing_job_description_count, 1)
        jd_chk = next(c for c in report.checks if "Job description" in c.check_name)
        self.assertEqual(jd_chk.issue_count, 1)

    def test_missing_required_skills_is_counted(self):
        self._create_app(company_name="Short", required_skills="y" * 9)
        report = build_data_quality_report(self.user)
        self.assertEqual(report.missing_required_skills_count, 1)
        sk_chk = next(c for c in report.checks if "Required skills" in c.check_name)
        self.assertEqual(sk_chk.issue_count, 1)

    def test_missing_follow_up_counted_only_for_active_statuses(self):
        self._create_app(
            company_name="SubNoFu",
            status=ApplicationStatus.SUBMITTED,
            follow_up_date=None,
        )
        self._create_app(
            company_name="RejNoFu",
            status=ApplicationStatus.REJECTED,
            follow_up_date=None,
        )
        report = build_data_quality_report(self.user)
        self.assertEqual(report.missing_follow_up_count, 1)
        fu_chk = next(c for c in report.checks if "Follow-up" in c.check_name)
        self.assertEqual(fu_chk.issue_count, 1)

    def test_follow_up_date_does_not_block_analytics_ready(self):
        self._create_app(
            company_name="ReadyNoFu",
            status=ApplicationStatus.SUBMITTED,
            follow_up_date=None,
        )
        report = build_data_quality_report(self.user)
        self.assertEqual(report.missing_follow_up_count, 1)
        self.assertEqual(report.analytics_ready_applications, 1)
        self.assertEqual(report.data_quality_score, 100.0)

    def test_analytics_ready_applications_counted_correctly(self):
        self._create_app(company_name="ReadyA")
        self._create_app(
            company_name="NotReady",
            cv_version="",
        )
        report = build_data_quality_report(self.user)
        self.assertEqual(report.analytics_ready_applications, 1)
        self.assertEqual(report.analytics_ready_rate, 50.0)

    def test_data_quality_score_matches_analytics_ready_rate(self):
        self._create_app(company_name="R1")
        self._create_app(company_name="R2", source=ApplicationSource.OTHER)
        self._create_app(company_name="R3", job_description="x" * 39)
        report = build_data_quality_report(self.user)
        expected = safe_percentage(report.analytics_ready_applications, report.total_applications)
        self.assertEqual(report.analytics_ready_rate, expected)
        self.assertEqual(report.data_quality_score, expected)
        self.assertEqual(report.data_quality_score, report.analytics_ready_rate)

    def test_check_severity_danger_when_completion_rate_below_70(self):
        for i in range(6):
            self._create_app(company_name=f"Ok{i}", date_applied=date(2026, 5, i + 1))
        for i in range(4):
            self._create_app(
                company_name=f"Bad{i}",
                date_applied=date(2026, 6, i + 1),
                source="",
            )
        report = build_data_quality_report(self.user)
        precise = next(c for c in report.checks if c.check_name == "Precise application source")
        self.assertEqual(precise.issue_count, 4)
        self.assertEqual(precise.completion_rate, 60.0)
        self.assertEqual(precise.severity, "danger")

    def test_check_severity_warning_when_issues_exist_but_completion_at_or_above_70(self):
        for i in range(8):
            self._create_app(company_name=f"Ok{i}", date_applied=date(2026, 5, i + 1))
        for i in range(2):
            self._create_app(
                company_name=f"Bad{i}",
                date_applied=date(2026, 6, i + 1),
                source="",
            )
        report = build_data_quality_report(self.user)
        precise = next(c for c in report.checks if c.check_name == "Precise application source")
        self.assertEqual(precise.issue_count, 2)
        self.assertEqual(precise.completion_rate, 80.0)
        self.assertEqual(precise.severity, "warning")

    def test_check_severity_success_when_issue_count_is_zero(self):
        self._create_app(company_name="Solo")
        report = build_data_quality_report(self.user)
        for c in report.checks:
            if c.issue_count == 0:
                self.assertEqual(c.severity, "success")

    def test_recommendations_returned_for_gaps(self):
        self._create_app(company_name="Gap", cv_version="", source=ApplicationSource.OTHER)
        report = build_data_quality_report(self.user)
        self.assertGreaterEqual(len(report.recommendations), 1)
        joined = " ".join(report.recommendations).lower()
        self.assertIn("source", joined)
        self.assertIn("cv", joined)


class MetricsViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_funnel_metrics_requires_login(self):
        response = self.client.get(reverse("metrics:funnel_metrics"))
        self.assertEqual(response.status_code, 302)

    def test_funnel_metrics_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("metrics:funnel_metrics"))
        self.assertEqual(response.status_code, 200)
