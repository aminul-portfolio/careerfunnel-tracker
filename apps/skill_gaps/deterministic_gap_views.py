"""Private transient deterministic JD Gap Analysis view (Sprint 110B Phase 2).

Isolated from provider-capable skill_gaps.views workflows.
"""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.skill_ledger.models import SkillEntry

from .deterministic_evidence_alignment import summarise_evidence_alignment
from .deterministic_gap_classifier import (
    SkillLedgerEvidence,
    classify_requirements,
)
from .forms import JDGapAnalysisForm


def _user_skill_ledger_evidence(user) -> tuple[SkillLedgerEvidence, ...]:
    rows = SkillEntry.objects.for_user(user).values(
        "id",
        "skill_name",
        "evidence_level",
    )
    return tuple(
        SkillLedgerEvidence(
            entry_id=row["id"],
            skill_name=row["skill_name"],
            evidence_level=row["evidence_level"],
        )
        for row in rows
    )


@login_required
def jd_gap_analysis_view(request):
    results = ()
    analysis_performed = False
    summary = None

    if request.method == "POST":
        form = JDGapAnalysisForm(request.POST)
        if form.is_valid():
            requirements = form.cleaned_data["normalised_requirements"]
            evidence = _user_skill_ledger_evidence(request.user)
            results = classify_requirements(requirements, evidence)
            summary = summarise_evidence_alignment(results)
            analysis_performed = True
    else:
        form = JDGapAnalysisForm()

    return render(
        request,
        "skill_gaps/jd_gap_analysis.html",
        {
            "form": form,
            "results": results,
            "analysis_performed": analysis_performed,
            "summary": summary,
        },
    )
