"""Private transient deterministic JD Gap Analysis view (Sprint 110B Phase 2).

Isolated from provider-capable skill_gaps.views workflows.
Sprint 114 Phase 4 adds an explicit second-POST advisory explanation path.
Sprint 117 Phase 2 adds a page-level feature-flag availability gate.
Sprint 118 Phase 2B reserves daily request governance before composition.
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
from .explanation_request_governance import (
    REASON_COUNT_LIMIT_REACHED,
    reserve_explanation_request,
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

_GOVERNANCE_COUNT_LIMIT_MESSAGE = (
    "The advisory explanation is unavailable because the current request "
    "limit has been reached. Your deterministic evidence-alignment result "
    "remains available and has not been changed."
)
_GOVERNANCE_GENERIC_UNAVAILABLE_MESSAGE = (
    "The advisory explanation is unavailable. Your deterministic "
    "evidence-alignment result remains available and has not been changed."
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


def _governance_block_message(reason_code: str | None) -> str:
    if reason_code == REASON_COUNT_LIMIT_REACHED:
        return _GOVERNANCE_COUNT_LIMIT_MESSAGE
    return _GOVERNANCE_GENERIC_UNAVAILABLE_MESSAGE


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
    explanation_governance_blocked = False
    explanation_governance_message = ""

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
                decision = reserve_explanation_request(request.user)
                if decision.allowed:
                    advisory_explanation, advisory_explanation_failed = (
                        _attempt_advisory_explanation(summary)
                    )
                else:
                    explanation_governance_blocked = True
                    explanation_governance_message = _governance_block_message(
                        decision.reason_code
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
            "explanation_governance_blocked": explanation_governance_blocked,
            "explanation_governance_message": explanation_governance_message,
        },
    )
