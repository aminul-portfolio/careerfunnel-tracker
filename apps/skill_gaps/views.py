from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.skill_ledger.models import SkillEntry
from apps.skill_ledger.selectors import get_skill_ledger_evidence_summary

from . import ai_career_coach
from .services import build_skill_gap_dashboard_context, build_skill_gap_ledger_match_rows

FILTER_NEEDS_EVIDENCE = [
    "NO_EVIDENCE",
    "NOT_IN_LEDGER",
]

EVIDENCE_FILTER_CHOICES = {
    "all",
    "verified",
    "learning_target",
    "studying",
    "no_evidence",
    "not_in_ledger",
    "needs_evidence",
}

EVIDENCE_FILTER_OPTIONS = (
    {"value": "all", "label": "All Skill Ledger statuses"},
    {"value": "verified", "label": "VERIFIED"},
    {"value": "learning_target", "label": "LEARNING_TARGET"},
    {"value": "studying", "label": "STUDYING"},
    {"value": "no_evidence", "label": "NO_EVIDENCE"},
    {"value": "not_in_ledger", "label": "Not in Skill Ledger"},
    {"value": "needs_evidence", "label": "Needs evidence"},
)


@login_required
@require_http_methods(["GET"])
def dashboard(request):
    evidence_filter = request.GET.get("evidence_filter", "all")
    if evidence_filter not in EVIDENCE_FILTER_CHOICES:
        evidence_filter = "all"

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
    if evidence_filter != "all":
        status_filter = {
            "verified": ("VERIFIED",),
            "learning_target": ("LEARNING_TARGET",),
            "studying": ("STUDYING",),
            "no_evidence": ("NO_EVIDENCE",),
            "not_in_ledger": ("NOT_IN_LEDGER",),
            "needs_evidence": tuple(FILTER_NEEDS_EVIDENCE),
        }[evidence_filter]
        skill_gap_ledger_match_rows = tuple(
            row
            for row in skill_gap_ledger_match_rows
            if row["ledger_status"] in status_filter
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
            "evidence_filter": evidence_filter,
            "evidence_filter_options": EVIDENCE_FILTER_OPTIONS,
        },
    )


@login_required
@require_http_methods(["GET"])
def ai_career_coach_view(request):
    context = build_skill_gap_dashboard_context(
        user=request.user,
        query_params={},
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
    matched_gap_rows = tuple(
        {
            "term": match_row["term"],
            "ledger_status": match_row["ledger_status"],
            "display_label": match_row["display_label"],
            "matched_skill_name": match_row["matched_skill_name"],
            "is_in_ledger": match_row["is_in_ledger"],
        }
        for match_row in skill_gap_ledger_matches
    )
    evidence_payload = ai_career_coach.build_evidence_payload(
        matched_gap_rows=matched_gap_rows,
    )
    controlled_prompt = ai_career_coach.build_controlled_prompt(evidence_payload)
    mocked_response = ai_career_coach.build_mocked_career_coach_response(
        evidence_payload,
    )
    validation_result = ai_career_coach.validate_career_coach_response(
        mocked_response,
        evidence_payload=evidence_payload,
    )
    safe_output = validation_result.safe_response if validation_result.is_valid else None
    return render(
        request,
        "skill_gaps/ai_career_coach.html",
        {
            "career_coach_output": safe_output,
            "validation_result": validation_result,
            "prompt_built": bool(controlled_prompt),
            "has_evidence_rows": bool(evidence_payload["matched_gap_rows"]),
            "has_skill_ledger_entries": bool(
                get_skill_ledger_evidence_summary()["total_entries"],
            ),
        },
    )
