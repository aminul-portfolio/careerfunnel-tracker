from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from .services import build_skill_gap_dashboard_context


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    context = build_skill_gap_dashboard_context(
        user=request.user,
        query_params=request.GET,
    )
    return render(
        request,
        "skill_gaps/dashboard.html",
        {
            "dashboard": context,
            "summary": context.summary,
            "skill_gaps": context.gaps,
            "priority_filter": context.priority_filter,
            "stage_filter": context.stage_filter,
            "resolved_filter": context.resolved_filter,
            "action_plan": context.action_plan,
        },
    )
