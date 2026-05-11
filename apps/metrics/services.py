from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.applications.choices import ApplicationStatus
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
