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


@login_required
@require_http_methods(["GET"])
def career_workflow_decision_assistant(request):
    workflow_principles = [
        {
            "title": "Review evidence before claiming a learning-target skill",
            "guidance": (
                "Before using a learning-target skill in a CV bullet or interview answer, "
                "check whether portfolio evidence, tests, screenshots, or prior work "
                "experience support the claim."
            ),
        },
        {
            "title": "Prioritise evidence-backed skills when tailoring a manual application",
            "guidance": (
                "When tailoring a manual application, lead with skills that already have "
                "reviewed evidence rather than skills still marked as learning targets."
            ),
        },
        {
            "title": "Check whether a manual follow-up is appropriate before drafting",
            "guidance": (
                "Before drafting follow-up text, confirm the application stage, saved notes, "
                "and whether a manual follow-up is appropriate for that role."
            ),
        },
        {
            "title": "Do not claim tools that are only learning targets",
            "guidance": (
                "Keep learning-target tools in a study or development plan until evidence "
                "is ready. Do not present them as verified proficiency."
            ),
        },
        {
            "title": "Improve evidence for repeated JD signals",
            "guidance": (
                "When the same skill appears across multiple job descriptions, treat it as "
                "a repeated signal to gather or strengthen evidence manually."
            ),
        },
        {
            "title": "Review weak-fit applications before investing tailoring time",
            "guidance": (
                "Review role fit, location, seniority, and evidence gaps before spending "
                "tailoring time on a weak-fit application."
            ),
        },
        {
            "title": "Add portfolio evidence for high-value skills",
            "guidance": (
                "For high-value skills that appear often in target roles, plan portfolio "
                "evidence, project notes, or sprint references before public claims."
            ),
        },
        {
            "title": "Continue the manual save and manual submit workflow",
            "guidance": (
                "Save application records manually, review evidence manually, and submit "
                "applications manually. Do not expect this page to save or send anything."
            ),
        },
    ]
    return render(
        request,
        "skills/career_workflow_decision_assistant.html",
        {"workflow_principles": workflow_principles},
    )
