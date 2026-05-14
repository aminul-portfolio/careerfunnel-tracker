from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Avg, Sum

from .models import DailyLog


@dataclass(frozen=True)
class DailyLogSummary:
    total_days_logged: int
    total_target_applications: int
    total_actual_applications: int
    total_variance: int
    total_cover_letters: int
    total_responses: int
    total_calls: int
    total_hours: Decimal
    average_energy: float
    target_hit_rate: float


def build_daily_log_summary(user) -> DailyLogSummary:
    logs = DailyLog.objects.filter(user=user)
    aggregate = logs.aggregate(
        target_sum=Sum("target_applications"),
        actual_sum=Sum("actual_applications"),
        cover_letter_sum=Sum("cover_letters_drafted"),
        response_sum=Sum("responses_received"),
        call_sum=Sum("calls_received"),
        hours_sum=Sum("hours_spent"),
        average_energy=Avg("energy_level"),
    )
    total_days = logs.count()
    total_target = aggregate["target_sum"] or 0
    total_actual = aggregate["actual_sum"] or 0
    target_hit_rate = (
        0.0
        if total_days == 0
        else round((sum(1 for log in logs if log.target_met) / total_days) * 100, 2)
    )
    return DailyLogSummary(
        total_days,
        total_target,
        total_actual,
        total_actual - total_target,
        aggregate["cover_letter_sum"] or 0,
        aggregate["response_sum"] or 0,
        aggregate["call_sum"] or 0,
        aggregate["hours_sum"] or Decimal("0.00"),
        round(aggregate["average_energy"] or 0, 2),
        target_hit_rate,
    )


def get_variance_badge_class(variance: int) -> str:
    if variance > 0:
        return "badge-success"
    if variance == 0:
        return "badge-primary"
    return "badge-danger"


def get_activity_signal_badge_class(signal: str) -> str:
    signal_map = {
        "No target set": "badge-muted",
        "No action taken": "badge-danger",
        "Below target": "badge-warning",
        "Target met": "badge-success",
        "Above target": "badge-success",
    }
    return signal_map.get(signal, "badge-neutral")


def build_daily_log_table_rows(logs):
    return [
        {
            "log": log,
            "variance_badge_class": get_variance_badge_class(log.variance),
            "signal_badge_class": get_activity_signal_badge_class(log.activity_signal),
        }
        for log in logs
    ]
