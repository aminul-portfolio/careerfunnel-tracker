"""Private transient deterministic JD Gap Analysis view (Sprint 110B Phase 2).

Isolated from provider-capable skill_gaps.views workflows.
Sprint 114 Phase 4 adds an explicit second-POST advisory explanation path.
Sprint 117 Phase 2 adds a page-level feature-flag availability gate.
"""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.ai_agents.provider_factory import (
    compose_evidence_alignment_explanation_provider,
)
from apps.skill_ledger.models import SkillEntry

from .deterministic_evidence_alignment import (
    EvidenceAlignmentOutcome,
    summarise_evidence_alignment,
)
from .deterministic_explanation_payload import (
    build_evidence_alignment_explanation_payload,
)
from .deterministic_gap_classifier import (
    SkillLedgerEvidence,
    classify_requirements,
)
from .explanation_output_validator import (
    validate_evidence_alignment_explanation_output,
)
from .forms import JDGapAnalysisForm

_PERMITTED_EXPLANATION_OUTCOMES = frozenset(
    {
        EvidenceAlignmentOutcome.ALL_REQUIREMENTS_VERIFIED,
        EvidenceAlignmentOutcome.SOME_REQUIREMENTS_VERIFIED,
        EvidenceAlignmentOutcome.DEVELOPMENT_RECORDS_ONLY,
        EvidenceAlignmentOutcome.NO_VERIFIED_EVIDENCE,
    }
)


def _explanation_feature_enabled() -> bool:
    """Fail-closed Boolean gate. Only an exact True enables the feature."""

    return (
        getattr(settings, "AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED", False)
        is True
    )


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


def _attempt_advisory_explanation(summary):
    """Run the allowlisted explanation pipeline once. Fail closed on any error.

    Returns (validated_dict_or_None, failed_bool).
    """
    try:
        provider = compose_evidence_alignment_explanation_provider()
        if provider is None:
            return None, True
        payload = build_evidence_alignment_explanation_payload(summary)
        raw_output = provider(payload)
        validated = validate_evidence_alignment_explanation_output(
            raw_output,
            payload,
        )
        return validated, False
    except Exception:
        return None, True


@login_required
def jd_gap_analysis_view(request):
    results = ()
    analysis_performed = False
    summary = None
    explanation_requested = (
        request.method == "POST"
        and request.POST.get("generate_explanation") == "1"
    )
    explanation_allowed = False
    explanation_feature_enabled = _explanation_feature_enabled()
    advisory_explanation = None
    advisory_explanation_failed = False

    if request.method == "POST":
        form = JDGapAnalysisForm(request.POST)
        if form.is_valid():
            requirements = form.cleaned_data["normalised_requirements"]
            evidence = _user_skill_ledger_evidence(request.user)
            results = classify_requirements(requirements, evidence)
            summary = summarise_evidence_alignment(results)
            analysis_performed = True
            explanation_allowed = summary.outcome in _PERMITTED_EXPLANATION_OUTCOMES
            if (
                explanation_requested
                and explanation_allowed
                and explanation_feature_enabled
            ):
                advisory_explanation, advisory_explanation_failed = (
                    _attempt_advisory_explanation(summary)
                )
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
            "explanation_requested": explanation_requested,
            "explanation_allowed": explanation_allowed,
            "explanation_feature_enabled": explanation_feature_enabled,
            "advisory_explanation": advisory_explanation,
            "advisory_explanation_failed": advisory_explanation_failed,
        },
    )
