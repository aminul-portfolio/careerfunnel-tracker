from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import build_reporting_foundation_context


@login_required
def funnel_metrics(request):
    return render(
        request,
        "metrics/funnel_metrics.html",
        build_reporting_foundation_context(request.user),
    )
