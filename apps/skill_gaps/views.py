from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.skill_ledger.models import SkillEntry
from apps.skill_ledger.selectors import get_skill_ledger_evidence_summary

from .services import build_skill_gap_dashboard_context, build_skill_gap_ledger_match_rows


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    context = build_skill_gap_dashboard_context(
        user=request.user,
        query_params=request.GET,
    )
    skill_gap_ledger_matches = build_skill_gap_ledger_match_rows(
        (
            {
                "term": gap.skill_name,
                "frequency": gap.failure_count,
            }
            for gap in context.gaps
        ),
        SkillEntry.objects.only("skill_name", "evidence_level"),
    )
    skill_gap_ledger_match_rows = tuple(
        {
            "gap": gap,
            **match_row,
        }
        for gap, match_row in zip(context.gaps, skill_gap_ledger_matches, strict=True)
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
            "learning_plan": context.learning_plan,
            "evidence_readiness": context.evidence_readiness,
            "portfolio_evidence_mapping": context.portfolio_evidence_mapping,
            "interview_story_mapping": context.interview_story_mapping,
            "cv_bullet_mapping": context.cv_bullet_mapping,
            "skill_ledger_summary": get_skill_ledger_evidence_summary(),
            "skill_gap_ledger_match_rows": skill_gap_ledger_match_rows,
        },
    )
