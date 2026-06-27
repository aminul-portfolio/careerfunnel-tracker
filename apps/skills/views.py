from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.skill_ledger.selectors import get_skill_ledger_evidence_summary

from .services.ai_capability_framework import (
    FRAMEWORK_CLAIM_SAFETY_NOTE,
    TOOL_EXAMPLES_DISCLAIMER,
    get_ai_capability_framework,
)
from .services.ai_readiness_scoring import build_portfolio_baseline_ai_readiness_score
from .services.career_readiness_dashboard import build_career_readiness_dashboard
from .services.career_strategy_action_plan import build_career_strategy_action_plan
from .services.final_career_intelligence_workflow import build_final_career_intelligence_workflow
from .services.job_ai_capability_matching import match_job_description_to_ai_capabilities
from .services.learning_recommendations import build_portfolio_baseline_learning_recommendations

DEMO_JOB_DESCRIPTION = (
    "Business analyst role using generative AI, prompt engineering, workflow automation, "
    "responsible AI governance, stakeholder reporting, and AI-assisted presentation decks."
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


@login_required
@require_http_methods(["GET"])
def job_ai_capability_match_report(request):
    return render(
        request,
        "skills/job_ai_capability_match_report.html",
        {
            "demo_job_description": DEMO_JOB_DESCRIPTION,
            "match_result": match_job_description_to_ai_capabilities(DEMO_JOB_DESCRIPTION),
        },
    )


@login_required
@require_http_methods(["GET"])
def learning_recommendations_report(request):
    return render(
        request,
        "skills/learning_recommendations_report.html",
        {
            "recommendations": build_portfolio_baseline_learning_recommendations(),
        },
    )


@login_required
@require_http_methods(["GET"])
def career_readiness_dashboard(request):
    return render(
        request,
        "skills/career_readiness_dashboard.html",
        {
            "dashboard": build_career_readiness_dashboard(),
        },
    )


@login_required
@require_http_methods(["GET"])
def career_strategy_action_plan(request):
    return render(
        request,
        "skills/career_strategy_action_plan.html",
        {
            "action_plan": build_career_strategy_action_plan(),
        },
    )


@login_required
@require_http_methods(["GET"])
def final_career_intelligence_workflow(request):
    return render(
        request,
        "skills/final_career_intelligence_workflow.html",
        {
            "skill_ledger_summary": get_skill_ledger_evidence_summary(),
            "workflow": build_final_career_intelligence_workflow(),
        },
    )
