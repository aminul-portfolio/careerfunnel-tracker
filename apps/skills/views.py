from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .services.ai_capability_framework import (
    FRAMEWORK_CLAIM_SAFETY_NOTE,
    TOOL_EXAMPLES_DISCLAIMER,
    get_ai_capability_framework,
)
from .services.ai_readiness_scoring import build_portfolio_baseline_ai_readiness_score


@login_required
@require_http_methods(["GET"])
def ai_capability_framework(request):
    return render(
        request,
        "skills/ai_capability_framework.html",
        {
            "capabilities": get_ai_capability_framework(),
            "framework_claim_safety_note": FRAMEWORK_CLAIM_SAFETY_NOTE,
            "tool_examples_disclaimer": TOOL_EXAMPLES_DISCLAIMER,
        },
    )


@login_required
@require_http_methods(["GET"])
def ai_readiness_report(request):
    return render(
        request,
        "skills/ai_readiness_report.html",
        {
            "readiness": build_portfolio_baseline_ai_readiness_score(),
        },
    )
