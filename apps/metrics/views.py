from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import (
    build_application_quality_report,
    build_cv_version_performance,
    build_data_quality_report,
    build_funnel_metrics,
    build_funnel_stage_rows,
    build_rejection_pattern_report,
    build_source_roi,
    build_weekly_trend,
    diagnose_funnel,
    get_diagnosis_panel_class,
)


@login_required
def funnel_metrics(request):
    metrics = build_funnel_metrics(request.user)
    diagnosis = diagnose_funnel(metrics)
    weekly_trend_rows = build_weekly_trend(request.user)
    weekly_trend_has_data = sum(
        1 for row in weekly_trend_rows if row.applications > 0
    ) >= 2
    return render(
        request,
        "metrics/funnel_metrics.html",
        {
            "metrics": metrics,
            "diagnosis": diagnosis,
            "funnel_stage_rows": build_funnel_stage_rows(metrics),
            "diagnosis_panel_class": get_diagnosis_panel_class(diagnosis.severity),
            "source_roi_rows": build_source_roi(request.user),
            "cv_version_rows": build_cv_version_performance(request.user),
            "rejection_report": build_rejection_pattern_report(request.user),
            "application_quality_report": build_application_quality_report(
                request.user
            ),
            "data_quality_report": build_data_quality_report(request.user),
            "weekly_trend_rows": weekly_trend_rows,
            "weekly_trend_has_data": weekly_trend_has_data,
        },
    )
