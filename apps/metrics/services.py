from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import CharField, Count, Q, Value
from django.db.models.functions import Coalesce, NullIf, Trim

from apps.applications.choices import ApplicationSource, ApplicationStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.weekly_review.choices import FunnelDiagnosis
from apps.weekly_review.models import WeeklyReview


@dataclass(frozen=True)
class FunnelMetrics:
    total_applications: int
    submitted_count: int
    acknowledged_count: int
    screening_call_count: int
    technical_screen_count: int
    interview_count: int
    offer_count: int
    rejected_count: int
    auto_rejected_count: int
    no_response_count: int
    response_count: int
    response_rate: float
    screening_rate: float
    interview_rate: float
    offer_rate: float
    rejection_rate: float
    daily_target_total: int
    daily_actual_total: int
    daily_variance_total: int
    daily_target_hit_rate: float
    total_hours_spent: Decimal
    weekly_reviews_count: int
    latest_weekly_diagnosis: str
    latest_weekly_diagnosis_label: str


@dataclass(frozen=True)
class SourceROIRow:
    source: str
    source_label: str
    total_applications: int
    responses: int
    interviews: int
    offers: int
    response_rate: float
    interview_rate: float
    offer_rate: float


@dataclass(frozen=True)
class CVVersionPerformanceRow:
    """One row of CV Version Performance analytics (grouped metrics, not A/B testing)."""

    cv_version: str
    total_applications: int
    responses: int
    interviews: int
    offers: int
    rejections: int
    response_rate: float
    interview_rate: float
    offer_rate: float
    rejection_rate: float


@dataclass(frozen=True)
class FunnelDiagnosisResult:
    diagnosis_code: str
    diagnosis_label: str
    diagnosis_title: str
    explanation: str
    recommended_action: str
    severity: str


def safe_percentage(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


_RESPONSE_STATUSES = (
    ApplicationStatus.ACKNOWLEDGED,
    ApplicationStatus.SCREENING_CALL,
    ApplicationStatus.TECHNICAL_SCREEN,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
    ApplicationStatus.AUTO_REJECTED,
)
_INTERVIEW_STATUSES = (ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER)


def _source_choice_label(code: str) -> str:
    try:
        return ApplicationSource(code).label
    except ValueError:
        return code or ApplicationSource.OTHER.label


def build_source_roi(user) -> list[SourceROIRow]:
    response_q = Q(status__in=_RESPONSE_STATUSES)
    interview_q = Q(status__in=_INTERVIEW_STATUSES)
    offer_q = Q(status=ApplicationStatus.OFFER)
    normalized_source = Coalesce(
        NullIf(Trim("source"), Value("", output_field=CharField())),
        Value(ApplicationSource.OTHER.value, output_field=CharField()),
        output_field=CharField(max_length=40),
    )
    groups = (
        JobApplication.objects.filter(user=user)
        .annotate(_roi_source=normalized_source)
        .values("_roi_source")
        .annotate(
            total_applications=Count("id"),
            responses=Count("id", filter=response_q),
            interviews=Count("id", filter=interview_q),
            offers=Count("id", filter=offer_q),
        )
    )
    rows: list[SourceROIRow] = []
    for row in groups:
        code = row["_roi_source"]
        total = row["total_applications"]
        responses = row["responses"]
        interviews = row["interviews"]
        offers = row["offers"]
        rows.append(
            SourceROIRow(
                source=code,
                source_label=_source_choice_label(code),
                total_applications=total,
                responses=responses,
                interviews=interviews,
                offers=offers,
                response_rate=safe_percentage(responses, total),
                interview_rate=safe_percentage(interviews, total),
                offer_rate=safe_percentage(offers, total),
            )
        )
    rows.sort(key=lambda r: (-r.response_rate, -r.interview_rate, -r.total_applications))
    return rows


def build_cv_version_performance(user) -> list[CVVersionPerformanceRow]:
    """Aggregate JobApplication rows into CV Version Performance metrics by cv_version."""
    response_q = Q(status__in=_RESPONSE_STATUSES)
    interview_q = Q(status__in=_INTERVIEW_STATUSES)
    offer_q = Q(status=ApplicationStatus.OFFER)
    rejection_q = Q(
        status__in=(ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED)
    )
    normalized_cv = Coalesce(
        NullIf(Trim("cv_version"), Value("", output_field=CharField())),
        Value("Unspecified", output_field=CharField()),
        output_field=CharField(max_length=120),
    )
    groups = (
        JobApplication.objects.filter(user=user)
        .annotate(_cv_perf_version=normalized_cv)
        .values("_cv_perf_version")
        .annotate(
            total_applications=Count("id"),
            responses=Count("id", filter=response_q),
            interviews=Count("id", filter=interview_q),
            offers=Count("id", filter=offer_q),
            rejections=Count("id", filter=rejection_q),
        )
    )
    rows: list[CVVersionPerformanceRow] = []
    for row in groups:
        version = row["_cv_perf_version"]
        total = row["total_applications"]
        responses = row["responses"]
        interviews = row["interviews"]
        offers = row["offers"]
        rejections = row["rejections"]
        rows.append(
            CVVersionPerformanceRow(
                cv_version=version,
                total_applications=total,
                responses=responses,
                interviews=interviews,
                offers=offers,
                rejections=rejections,
                response_rate=safe_percentage(responses, total),
                interview_rate=safe_percentage(interviews, total),
                offer_rate=safe_percentage(offers, total),
                rejection_rate=safe_percentage(rejections, total),
            )
        )
    rows.sort(
        key=lambda r: (-r.response_rate, -r.interview_rate, -r.total_applications)
    )
    return rows


_REJECTION_STATUSES = (ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED)
_REJECTION_Q = Q(status__in=_REJECTION_STATUSES)
_AUTO_REJECTION_Q = Q(status=ApplicationStatus.AUTO_REJECTED)

_SENIORITY_SIGNALS = (
    "senior",
    "lead",
    "principal",
    "manager",
    "head of",
    "3+ years",
    "5+ years",
    "minimum 3",
    "minimum 5",
)


def _seniority_risk_q() -> Q:
    q = Q()
    for field in ("job_title", "required_skills", "job_description"):
        for sig in _SENIORITY_SIGNALS:
            q |= Q(**{f"{field}__icontains": sig})
    return q


_SAMPLE_WARNING_LOW_VOLUME = (
    "Not enough applications yet for strong pattern conclusions. Treat this as directional only."
)


@dataclass(frozen=True)
class RejectionGroupRow:
    """Per-source rejection counts and rates (denominator = all applications from that source)."""

    source: str
    source_label: str
    rejection_count: int
    total_applications: int
    rejection_rate: float


@dataclass(frozen=True)
class RejectionCvVersionRow:
    """Per-CV-version rejection counts and rates (denominator = all applications using that version)."""

    cv_version: str
    rejection_count: int
    total_applications: int
    rejection_rate: float


@dataclass(frozen=True)
class RejectionPatternReport:
    total_applications: int
    total_rejections: int
    auto_rejections: int
    rejection_rate: float
    auto_rejection_rate: float
    has_enough_data: bool
    sample_warning: str
    by_source: tuple[RejectionGroupRow, ...]
    by_cv_version: tuple[RejectionCvVersionRow, ...]
    seniority_risk_count: int
    recommendations: tuple[str, ...]


def _build_rejection_recommendations(
    *,
    total_applications: int,
    total_rejections: int,
    auto_rejections: int,
    auto_rejection_rate: float,
    seniority_risk_count: int,
    by_source: tuple[RejectionGroupRow, ...],
    overall_rejection_rate: float,
) -> tuple[str, ...]:
    recs: list[str] = []

    if total_applications == 0:
        recs.append(
            "Log job applications in the tracker first; rejection pattern analysis needs application history."
        )
        return tuple(recs)

    if total_applications < 20:
        recs.append(
            "Collect at least 20 logged applications before drawing strong conclusions from rejection patterns."
        )

    auto_high = auto_rejection_rate >= 25.0 and auto_rejections > 0
    if auto_high:
        recs.append(
            "Auto-rejection rate is elevated; review CV targeting, keywords, and whether each role is a realistic fit."
        )

    if seniority_risk_count > 0:
        recs.append(
            "Several rejections align with senior or stretch-role signals; consider narrowing to roles that match your level."
        )

    source_hotspot = False
    if by_source and total_rejections >= 3:
        top_source = max(by_source, key=lambda r: (r.rejection_count, r.total_applications))
        source_hotspot = (
            top_source.rejection_count >= 3
            and top_source.rejection_rate >= 40.0
            and top_source.rejection_count >= max(1, int(0.35 * total_rejections))
        )
        if source_hotspot:
            recs.append(
                f"Review the {top_source.source_label} channel: it shows a concentration of rejections relative to volume."
            )

    if total_applications >= 20:
        if not auto_high and seniority_risk_count == 0 and not source_hotspot:
            if overall_rejection_rate < 70.0:
                recs.append(
                    "No single major red flag detected; keep logging applications and compare rejection rates across sources and CV versions."
                )
            else:
                recs.append(
                    "Overall rejection rate is high; continue refining targeting while comparing sources and CV versions side by side."
                )

    if not recs:
        recs.append(
            "Continue logging applications and compare sources and CV versions as more outcomes arrive."
        )

    return tuple(recs)


def build_rejection_pattern_report(user) -> RejectionPatternReport:
    base = JobApplication.objects.filter(user=user)
    total_applications = base.count()
    total_rejections = base.filter(_REJECTION_Q).count()
    auto_rejections = base.filter(_AUTO_REJECTION_Q).count()
    rejection_rate = safe_percentage(total_rejections, total_applications)
    auto_rejection_rate = safe_percentage(auto_rejections, total_applications)

    has_enough_data = total_applications >= 20
    sample_warning = "" if has_enough_data else _SAMPLE_WARNING_LOW_VOLUME

    normalized_source = Coalesce(
        NullIf(Trim("source"), Value("", output_field=CharField())),
        Value(ApplicationSource.OTHER.value, output_field=CharField()),
        output_field=CharField(max_length=40),
    )
    source_groups = (
        JobApplication.objects.filter(user=user)
        .annotate(_rej_source=normalized_source)
        .values("_rej_source")
        .annotate(
            total_applications=Count("id"),
            rejection_count=Count("id", filter=_REJECTION_Q),
        )
    )
    by_source_list: list[RejectionGroupRow] = []
    for row in source_groups:
        code = row["_rej_source"]
        total = row["total_applications"]
        rej = row["rejection_count"]
        by_source_list.append(
            RejectionGroupRow(
                source=code,
                source_label=_source_choice_label(code),
                rejection_count=rej,
                total_applications=total,
                rejection_rate=safe_percentage(rej, total),
            )
        )
    by_source_list.sort(
        key=lambda r: (-r.rejection_count, -r.total_applications, r.source_label)
    )
    by_source = tuple(by_source_list)

    normalized_cv = Coalesce(
        NullIf(Trim("cv_version"), Value("", output_field=CharField())),
        Value("Unspecified", output_field=CharField()),
        output_field=CharField(max_length=120),
    )
    cv_groups = (
        JobApplication.objects.filter(user=user)
        .annotate(_rej_cv=normalized_cv)
        .values("_rej_cv")
        .annotate(
            total_applications=Count("id"),
            rejection_count=Count("id", filter=_REJECTION_Q),
        )
    )
    by_cv_list: list[RejectionCvVersionRow] = []
    for row in cv_groups:
        version = row["_rej_cv"]
        total = row["total_applications"]
        rej = row["rejection_count"]
        by_cv_list.append(
            RejectionCvVersionRow(
                cv_version=version,
                rejection_count=rej,
                total_applications=total,
                rejection_rate=safe_percentage(rej, total),
            )
        )
    by_cv_list.sort(
        key=lambda r: (-r.rejection_count, -r.total_applications, r.cv_version)
    )
    by_cv_version = tuple(by_cv_list)

    seniority_risk_count = base.filter(_REJECTION_Q & _seniority_risk_q()).count()

    recommendations = _build_rejection_recommendations(
        total_applications=total_applications,
        total_rejections=total_rejections,
        auto_rejections=auto_rejections,
        auto_rejection_rate=auto_rejection_rate,
        seniority_risk_count=seniority_risk_count,
        by_source=by_source,
        overall_rejection_rate=rejection_rate,
    )

    return RejectionPatternReport(
        total_applications=total_applications,
        total_rejections=total_rejections,
        auto_rejections=auto_rejections,
        rejection_rate=rejection_rate,
        auto_rejection_rate=auto_rejection_rate,
        has_enough_data=has_enough_data,
        sample_warning=sample_warning,
        by_source=by_source,
        by_cv_version=by_cv_version,
        seniority_risk_count=seniority_risk_count,
        recommendations=recommendations,
    )


def build_funnel_metrics(user) -> FunnelMetrics:
    applications = JobApplication.objects.filter(user=user)
    total_applications = applications.count()
    submitted_count = applications.filter(status=ApplicationStatus.SUBMITTED).count()
    acknowledged_count = applications.filter(status=ApplicationStatus.ACKNOWLEDGED).count()
    screening_call_count = applications.filter(status=ApplicationStatus.SCREENING_CALL).count()
    technical_screen_count = applications.filter(status=ApplicationStatus.TECHNICAL_SCREEN).count()
    interview_count = applications.filter(status=ApplicationStatus.INTERVIEW).count()
    offer_count = applications.filter(status=ApplicationStatus.OFFER).count()
    rejected_count = applications.filter(status=ApplicationStatus.REJECTED).count()
    auto_rejected_count = applications.filter(status=ApplicationStatus.AUTO_REJECTED).count()
    no_response_count = applications.filter(status=ApplicationStatus.NO_RESPONSE).count()
    response_statuses = [ApplicationStatus.ACKNOWLEDGED, ApplicationStatus.SCREENING_CALL, ApplicationStatus.TECHNICAL_SCREEN, ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER, ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED]
    response_count = applications.filter(status__in=response_statuses).count()
    screening_stage_count = screening_call_count + technical_screen_count + interview_count + offer_count
    interview_stage_count = interview_count + offer_count
    rejection_total = rejected_count + auto_rejected_count
    daily_logs = DailyLog.objects.filter(user=user)
    daily_target_total = sum(log.target_applications for log in daily_logs)
    daily_actual_total = sum(log.actual_applications for log in daily_logs)
    daily_logs_count = daily_logs.count()
    daily_target_hit_rate = 0.0 if daily_logs_count == 0 else safe_percentage(sum(1 for log in daily_logs if log.target_met), daily_logs_count)
    total_hours_spent = sum((log.hours_spent for log in daily_logs), Decimal("0.00"))
    weekly_reviews = WeeklyReview.objects.filter(user=user)
    latest_weekly_review = weekly_reviews.first()
    if latest_weekly_review:
        latest_weekly_diagnosis = latest_weekly_review.diagnosis
        latest_weekly_diagnosis_label = latest_weekly_review.get_diagnosis_display()
    else:
        latest_weekly_diagnosis = FunnelDiagnosis.UNKNOWN
        latest_weekly_diagnosis_label = "Unknown / not enough data"
    return FunnelMetrics(total_applications, submitted_count, acknowledged_count, screening_call_count, technical_screen_count, interview_count, offer_count, rejected_count, auto_rejected_count, no_response_count, response_count, safe_percentage(response_count, total_applications), safe_percentage(screening_stage_count, total_applications), safe_percentage(interview_stage_count, total_applications), safe_percentage(offer_count, total_applications), safe_percentage(rejection_total, total_applications), daily_target_total, daily_actual_total, daily_actual_total - daily_target_total, daily_target_hit_rate, total_hours_spent, weekly_reviews.count(), latest_weekly_diagnosis, latest_weekly_diagnosis_label)


def diagnose_funnel(metrics: FunnelMetrics) -> FunnelDiagnosisResult:
    if metrics.total_applications == 0:
        return FunnelDiagnosisResult(FunnelDiagnosis.UNKNOWN, "Unknown / not enough data", "No application data yet", "There are no logged applications yet, so the platform cannot diagnose where the funnel is leaking.", "Start by logging every application you submit. After 10 to 15 applications, the funnel diagnosis becomes more meaningful.", "neutral")
    if metrics.daily_actual_total == 0 and metrics.daily_target_total > 0:
        return FunnelDiagnosisResult(FunnelDiagnosis.LOW_ACTIVITY, "Low activity / consistency issue", "The main issue is activity volume", "You set application targets, but the actual number of applications is still zero. This suggests the first bottleneck is execution consistency.", "Reduce the daily target if needed, but submit applications consistently.", "danger")
    if metrics.total_applications < 10:
        return FunnelDiagnosisResult(FunnelDiagnosis.UNKNOWN, "Unknown / not enough data", "Not enough volume for a reliable diagnosis", "The tracker has fewer than 10 applications. That is not enough data to judge whether the problem is CV targeting, screening, or interviews.", "Reach at least 10 properly targeted applications before making a strong conclusion.", "warning")
    if metrics.response_rate == 0:
        return FunnelDiagnosisResult(FunnelDiagnosis.CV_TARGETING, "CV / targeting issue", "Applications are not converting into responses", "You have enough application volume, but the response rate is zero. This usually points to a CV-positioning issue, role targeting issue, or mismatch between the job requirements and the evidence shown in the application.", "Review the CV headline, project evidence, keywords, and job targeting.", "danger")
    if metrics.response_rate < 10:
        return FunnelDiagnosisResult(FunnelDiagnosis.CV_TARGETING, "CV / targeting issue", "Response rate is weak", "The response rate is below 10%. That suggests applications are getting some traction, but not enough to show strong role alignment.", "Tighten targeting. Focus on roles where your analytics evidence directly matches the role.", "warning")
    if metrics.response_count > 0 and metrics.screening_rate == 0:
        return FunnelDiagnosisResult(FunnelDiagnosis.MESSAGING_FIT, "Messaging / role-fit issue", "Responses are not becoming screening calls", "You are getting some responses, but they are not converting into screening calls.", "Improve cover-letter clarity and recruiter follow-up.", "warning")
    if metrics.screening_rate > 0 and metrics.interview_rate == 0:
        return FunnelDiagnosisResult(FunnelDiagnosis.SCREENING, "Screening-call issue", "Screening calls are not becoming interviews", "The funnel is reaching screening calls but not progressing into interviews.", "Prepare a stronger 60-second profile answer and clear project explanations.", "warning")
    if metrics.interview_rate > 0 and metrics.offer_rate == 0:
        return FunnelDiagnosisResult(FunnelDiagnosis.INTERVIEW, "Interview performance issue", "Interviews are not becoming offers yet", "You are reaching interviews, which means the CV and initial screening are working. The current bottleneck is likely interview evidence or technical confidence.", "Practise project walkthroughs, SQL/Python/Excel interview questions, and business-case explanations.", "primary")
    if metrics.offer_rate > 0:
        return FunnelDiagnosisResult(FunnelDiagnosis.STRATEGY_WORKING, "Strategy working", "The funnel is producing offers", "The application funnel has reached offer stage. That means the overall strategy is working.", "Review which roles converted best and double down on similar job titles.", "success")
    return FunnelDiagnosisResult(FunnelDiagnosis.UNKNOWN, "Unknown / not enough data", "Diagnosis is unclear", "The current data does not point clearly to one funnel problem yet.", "Keep logging applications, responses, calls, and interviews.", "neutral")


def get_diagnosis_panel_class(severity: str) -> str:
    return {"success": "diagnosis-success", "primary": "diagnosis-primary", "warning": "diagnosis-warning", "danger": "diagnosis-danger", "neutral": "diagnosis-neutral"}.get(severity, "diagnosis-neutral")


def build_funnel_stage_rows(metrics: FunnelMetrics):
    return [
        {"stage": "Applications Submitted", "count": metrics.total_applications, "rate": "100%", "description": "Total number of logged job applications."},
        {"stage": "Responses Received", "count": metrics.response_count, "rate": f"{metrics.response_rate}%", "description": "Applications that received any company response."},
        {"stage": "Screening / Technical Stage", "count": metrics.screening_call_count + metrics.technical_screen_count, "rate": f"{metrics.screening_rate}%", "description": "Applications that reached screening call or technical screen."},
        {"stage": "Interview Stage", "count": metrics.interview_count, "rate": f"{metrics.interview_rate}%", "description": "Applications that reached interview stage."},
        {"stage": "Offer Stage", "count": metrics.offer_count, "rate": f"{metrics.offer_rate}%", "description": "Applications that reached offer stage."},
    ]
