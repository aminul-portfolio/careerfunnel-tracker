from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .services.ai_capability_framework import (
    FRAMEWORK_CLAIM_SAFETY_NOTE,
    TOOL_EXAMPLES_DISCLAIMER,
    get_ai_capability_framework,
)


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
