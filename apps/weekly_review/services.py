from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Sum

from .choices import FunnelDiagnosis
from .models import WeeklyReview


@dataclass(frozen=True)
class WeeklyReviewSummary:
    total_weeks_reviewed: int
    total_target_applications: int
    total_actual_applications: int
    total_variance: int
    total_responses: int
    total_screening_calls: int
    total_interviews: int
    total_offers: int
    average_response_rate: float
    average_interview_rate: float
    average_offer_rate: float


def build_weekly_review_summary(user) -> WeeklyReviewSummary:
    reviews = WeeklyReview.objects.filter(user=user)
    aggregate = reviews.aggregate(
        target_sum=Sum("target_applications"),
        actual_sum=Sum("actual_applications"),
        responses_sum=Sum("responses_received"),
        screening_sum=Sum("screening_calls"),
        interviews_sum=Sum("interviews"),
        offers_sum=Sum("offers"),
    )
    total_target = aggregate["target_sum"] or 0
    total_actual = aggregate["actual_sum"] or 0
    total_responses = aggregate["responses_sum"] or 0
    total_interviews = aggregate["interviews_sum"] or 0
    total_offers = aggregate["offers_sum"] or 0
    if total_actual == 0:
        average_response_rate = average_interview_rate = average_offer_rate = 0.0
    else:
        average_response_rate = round((total_responses / total_actual) * 100, 2)
        average_interview_rate = round((total_interviews / total_actual) * 100, 2)
        average_offer_rate = round((total_offers / total_actual) * 100, 2)
    return WeeklyReviewSummary(
        reviews.count(),
        total_target,
        total_actual,
        total_actual - total_target,
        total_responses,
        aggregate["screening_sum"] or 0,
        total_interviews,
        total_offers,
        average_response_rate,
        average_interview_rate,
        average_offer_rate,
    )


def get_variance_badge_class(variance: int) -> str:
    if variance > 0:
        return "badge-success"
    if variance == 0:
        return "badge-primary"
    return "badge-danger"


def get_diagnosis_badge_class(diagnosis: str) -> str:
    diagnosis_map = {
        FunnelDiagnosis.LOW_ACTIVITY: "badge-danger",
        FunnelDiagnosis.CV_TARGETING: "badge-warning",
        FunnelDiagnosis.MESSAGING_FIT: "badge-warning",
        FunnelDiagnosis.SCREENING: "badge-info",
        FunnelDiagnosis.INTERVIEW: "badge-primary",
        FunnelDiagnosis.STRATEGY_WORKING: "badge-success",
        FunnelDiagnosis.UNKNOWN: "badge-muted",
    }
    return diagnosis_map.get(diagnosis, "badge-neutral")


def build_weekly_review_table_rows(reviews):
    return [
        {
            "review": review,
            "variance_badge_class": get_variance_badge_class(
                review.application_variance
            ),
            "diagnosis_badge_class": get_diagnosis_badge_class(review.diagnosis),
        }
        for review in reviews
    ]


def suggest_diagnosis(
    actual_applications: int,
    responses_received: int,
    screening_calls: int,
    interviews: int,
    offers: int,
) -> str:
    if actual_applications == 0:
        return FunnelDiagnosis.LOW_ACTIVITY
    response_rate = responses_received / actual_applications
    if actual_applications >= 10 and response_rate == 0:
        return FunnelDiagnosis.CV_TARGETING
    if responses_received > 0 and screening_calls == 0:
        return FunnelDiagnosis.MESSAGING_FIT
    if screening_calls > 0 and interviews == 0:
        return FunnelDiagnosis.SCREENING
    if interviews > 0 and offers == 0:
        return FunnelDiagnosis.INTERVIEW
    if offers > 0:
        return FunnelDiagnosis.STRATEGY_WORKING
    return FunnelDiagnosis.UNKNOWN
