from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import build_funnel_metrics, build_funnel_stage_rows, diagnose_funnel, get_diagnosis_panel_class


@login_required
def funnel_metrics(request):
    metrics = build_funnel_metrics(request.user)
    diagnosis = diagnose_funnel(metrics)
    return render(request, "metrics/funnel_metrics.html", {"metrics": metrics, "diagnosis": diagnosis, "funnel_stage_rows": build_funnel_stage_rows(metrics), "diagnosis_panel_class": get_diagnosis_panel_class(diagnosis.severity)})
