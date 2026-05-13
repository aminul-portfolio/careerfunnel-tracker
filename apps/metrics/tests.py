from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import ApplicationSource, ApplicationStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog

from .services import (
    build_cv_version_performance,
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
        JobApplication.objects.create(user=self.user, company_name="Company A", job_title="Data Analyst", date_applied=date(2026, 5, 1), status=ApplicationStatus.SUBMITTED)
        JobApplication.objects.create(user=self.user, company_name="Company B", job_title="BI Analyst", date_applied=date(2026, 5, 2), status=ApplicationStatus.ACKNOWLEDGED)
        JobApplication.objects.create(user=self.user, company_name="Company C", job_title="Reporting Analyst", date_applied=date(2026, 5, 3), status=ApplicationStatus.INTERVIEW)
        metrics = build_funnel_metrics(self.user)
        self.assertEqual(metrics.total_applications, 3)
        self.assertEqual(metrics.response_count, 2)
        self.assertEqual(metrics.response_rate, 66.67)

    def test_metrics_calculates_daily_log_totals(self):
        DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 9), target_applications=3, actual_applications=2, hours_spent=Decimal("2.50"), energy_level=4)
        DailyLog.objects.create(user=self.user, log_date=date(2026, 5, 10), target_applications=3, actual_applications=3, hours_spent=Decimal("3.00"), energy_level=4)
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
        self._create_app(source=ApplicationSource.REED, company_name="C1", status=ApplicationStatus.SUBMITTED)
        self._create_app(source=ApplicationSource.REED, company_name="C2", status=ApplicationStatus.SUBMITTED)
        self._create_app(source=ApplicationSource.REED, company_name="C3", status=ApplicationStatus.ACKNOWLEDGED)
        self._create_app(source=ApplicationSource.REED, company_name="C4", status=ApplicationStatus.AUTO_REJECTED)
        rows = build_source_roi(self.user)
        reed = next(r for r in rows if r.source == ApplicationSource.REED)
        self.assertEqual(reed.responses, 2)
        self.assertEqual(reed.total_applications, 4)
        self.assertEqual(reed.response_rate, 50.0)

    def test_build_source_roi_interview_rate_counts_interview_and_offer(self):
        self._create_app(source=ApplicationSource.GLASSDOOR, company_name="G1", status=ApplicationStatus.SUBMITTED)
        self._create_app(source=ApplicationSource.GLASSDOOR, company_name="G2", status=ApplicationStatus.INTERVIEW)
        self._create_app(source=ApplicationSource.GLASSDOOR, company_name="G3", status=ApplicationStatus.INTERVIEW)
        self._create_app(source=ApplicationSource.GLASSDOOR, company_name="G4", status=ApplicationStatus.OFFER)
        self._create_app(source=ApplicationSource.GLASSDOOR, company_name="G5", status=ApplicationStatus.ACKNOWLEDGED)
        rows = build_source_roi(self.user)
        g = next(r for r in rows if r.source == ApplicationSource.GLASSDOOR)
        self.assertEqual(g.interviews, 3)
        self.assertEqual(g.total_applications, 5)
        self.assertEqual(g.interview_rate, 60.0)

    def test_build_source_roi_offer_rate(self):
        self._create_app(source=ApplicationSource.REFERRAL, company_name="R1", status=ApplicationStatus.OFFER)
        self._create_app(source=ApplicationSource.REFERRAL, company_name="R2", status=ApplicationStatus.INTERVIEW)
        self._create_app(source=ApplicationSource.REFERRAL, company_name="R3", status=ApplicationStatus.SUBMITTED)
        self._create_app(source=ApplicationSource.REFERRAL, company_name="R4", status=ApplicationStatus.SUBMITTED)
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
        self._create_app(source=ApplicationSource.LINKEDIN, company_name="L1", status=ApplicationStatus.ACKNOWLEDGED)
        self._create_app(source=ApplicationSource.LINKEDIN, company_name="L2", status=ApplicationStatus.ACKNOWLEDGED)
        self._create_app(source=ApplicationSource.INDEED, company_name="I1", status=ApplicationStatus.SUBMITTED)
        self._create_app(source=ApplicationSource.INDEED, company_name="I2", status=ApplicationStatus.SUBMITTED)
        self._create_app(source=ApplicationSource.INDEED, company_name="I3", status=ApplicationStatus.SUBMITTED)
        self._create_app(source=ApplicationSource.INDEED, company_name="I4", status=ApplicationStatus.SUBMITTED)
        rows = build_source_roi(self.user)
        self.assertEqual([r.source for r in rows], [ApplicationSource.LINKEDIN, ApplicationSource.INDEED])


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
        self._create_app(cv_version="v-test", company_name="C1", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="v-test", company_name="C2", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="v-test", company_name="C3", status=ApplicationStatus.ACKNOWLEDGED)
        self._create_app(cv_version="v-test", company_name="C4", status=ApplicationStatus.AUTO_REJECTED)
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
        self._create_app(cv_version="v-int", company_name="G5", status=ApplicationStatus.ACKNOWLEDGED)
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
        self._create_app(cv_version="v-rej", company_name="J2", status=ApplicationStatus.AUTO_REJECTED)
        self._create_app(cv_version="v-rej", company_name="J3", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="v-rej", company_name="J4", status=ApplicationStatus.ACKNOWLEDGED)
        rows = build_cv_version_performance(self.user)
        row = next(r for r in rows if r.cv_version == "v-rej")
        self.assertEqual(row.rejections, 2)
        self.assertEqual(row.total_applications, 4)
        self.assertEqual(row.rejection_rate, 50.0)

    def test_build_cv_version_performance_sorts_by_response_then_interview_then_volume(self):
        self._create_app(cv_version="high-response", company_name="H1", status=ApplicationStatus.ACKNOWLEDGED)
        self._create_app(cv_version="high-response", company_name="H2", status=ApplicationStatus.ACKNOWLEDGED)
        self._create_app(cv_version="low-response", company_name="L1", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="low-response", company_name="L2", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="low-response", company_name="L3", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="low-response", company_name="L4", status=ApplicationStatus.SUBMITTED)
        rows = build_cv_version_performance(self.user)
        self.assertEqual([r.cv_version for r in rows], ["high-response", "low-response"])


class RejectionPatternReportTests(TestCase):
    """Tests for rejection pattern analytics (Sprint 2B Task 1)."""

    _LOW_SAMPLE_WARNING = (
        "Not enough applications yet for strong pattern conclusions. Treat this as directional only."
    )

    def setUp(self):
        self.user = User.objects.create_user(username="rej_pattern_user", password="StrongPass12345")

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
        self._create_app(cv_version="vA", company_name="A1", status=ApplicationStatus.REJECTED)
        self._create_app(cv_version="vA", company_name="A2", status=ApplicationStatus.SUBMITTED)
        self._create_app(cv_version="vB", company_name="B1", status=ApplicationStatus.AUTO_REJECTED)
        report = build_rejection_pattern_report(self.user)
        by_cv = {r.cv_version: r for r in report.by_cv_version}
        self.assertEqual(by_cv["vA"].rejection_count, 1)
        self.assertEqual(by_cv["vA"].total_applications, 2)
        self.assertEqual(by_cv["vA"].rejection_rate, 50.0)
        self.assertEqual(by_cv["vB"].rejection_count, 1)
        self.assertEqual(by_cv["vB"].rejection_rate, 100.0)

    def test_blank_cv_version_normalized_to_unspecified(self):
        self._create_app(cv_version="", company_name="U1", status=ApplicationStatus.REJECTED)
        self._create_app(cv_version="   ", company_name="U2", status=ApplicationStatus.AUTO_REJECTED)
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
