from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .advisory import (
    ADVISORY_CLASSIFICATIONS,
    REQUIRED_JD_SIGNAL_SAFETY_WORDING,
    REQUIRED_SKILL_ADVISORY_SAFETY_WORDING,
    advisory_row_to_template_dict,
    build_skill_advisory_rows,
    collect_jd_candidate_terms,
)
from .ai_explanation import (
    FORBIDDEN_EXPLANATION_PHRASES,
    REQUIRED_EXPLANATION_SAFETY_WARNING,
    SPRINT_87_PROVIDER_MODE_MOCKED,
    build_skill_advisory_explanations,
    explanation_to_dict,
)
from .embedding_provider import DeterministicOfflineEmbeddingProvider
from .forms import SkillEntryForm
from .models import SkillEntry
from .rag_generation import (
    QUERY_MAX_LEN,
    RagRejectionCode,
    generate_grounded_rag_answer,
)
from .rag_retrieval import EvidenceRetrievalError, retrieve_owned_skill_evidence


def resolve_skill_ledger_public_owner():
    """Return the configured active public owner, or None when resolution fails closed."""
    configured_username = str(
        getattr(settings, "SKILL_LEDGER_PUBLIC_OWNER_USERNAME", "") or ""
    ).strip()
    if not configured_username:
        return None
    User = get_user_model()
    matches = list(
        User.objects.filter(
            username=configured_username,
            is_active=True,
        )[:2]
    )
    if len(matches) != 1:
        return None
    return matches[0]


@login_required
def skill_ledger_list(request):
    search_query = request.GET.get("q", "").strip()
    all_entries = SkillEntry.objects.for_user(request.user)
    entries = all_entries
    if search_query:
        entries = entries.filter(skill_name__icontains=search_query)
    entries = entries.order_by("evidence_level", "category", "skill_name")

    evidence_groups = [
        {
            "value": SkillEntry.EvidenceLevel.VERIFIED,
            "label": "Verified",
            "entries": [],
        },
        {
            "value": SkillEntry.EvidenceLevel.LEARNING_TARGET,
            "label": "Learning Target",
            "entries": [],
        },
        {
            "value": SkillEntry.EvidenceLevel.STUDYING,
            "label": "Studying",
            "entries": [],
        },
        {
            "value": SkillEntry.EvidenceLevel.NO_EVIDENCE,
            "label": "No Evidence",
            "entries": [],
        },
    ]
    entries_by_level = {group["value"]: group["entries"] for group in evidence_groups}
    for entry in entries:
        entries_by_level[entry.evidence_level].append(entry)

    kpi_counts = {
        group["value"]: all_entries.filter(evidence_level=group["value"]).count()
        for group in evidence_groups
    }

    return render(
        request,
        "skill_ledger/skill_ledger_list.html",
        {
            "entries": entries,
            "evidence_groups": evidence_groups,
            "kpi_counts": kpi_counts,
            "search_query": search_query,
        },
    )


@require_GET
def skill_ledger_public(request):
    search_query = request.GET.get("q", "").strip()
    public_evidence_levels = [
        SkillEntry.EvidenceLevel.VERIFIED,
        SkillEntry.EvidenceLevel.LEARNING_TARGET,
    ]
    public_owner = resolve_skill_ledger_public_owner()
    if public_owner is None:
        public_entries = SkillEntry.objects.none()
    else:
        public_entries = SkillEntry.objects.filter(
            user=public_owner,
            visibility=SkillEntry.Visibility.PUBLIC,
            evidence_level__in=public_evidence_levels,
        )
    entries = public_entries
    if search_query:
        entries = entries.filter(skill_name__icontains=search_query)
    entries = entries.order_by("evidence_level", "category", "skill_name")

    evidence_groups = [
        {
            "value": SkillEntry.EvidenceLevel.VERIFIED,
            "label": "Verified",
            "entries": [],
        },
        {
            "value": SkillEntry.EvidenceLevel.LEARNING_TARGET,
            "label": "Learning Target",
            "entries": [],
        },
    ]
    entries_by_level = {group["value"]: group["entries"] for group in evidence_groups}
    for entry in entries:
        entries_by_level[entry.evidence_level].append(entry)

    kpi_counts = {
        group["value"]: public_entries.filter(evidence_level=group["value"]).count()
        for group in evidence_groups
    }

    return render(
        request,
        "skill_ledger/skill_ledger_public.html",
        {
            "entries": entries,
            "evidence_groups": evidence_groups,
            "kpi_counts": kpi_counts,
            "search_query": search_query,
        },
    )


@login_required
@require_GET
def skill_ledger_advisory(request):
    entries = SkillEntry.objects.for_user(request.user).order_by(
        "evidence_level",
        "category",
        "skill_name",
    )
    jd_candidate_terms = collect_jd_candidate_terms(request.user)
    advisory_rows = build_skill_advisory_rows(entries, jd_candidate_terms=jd_candidate_terms)
    template_rows = tuple(advisory_row_to_template_dict(row) for row in advisory_rows)
    return render(
        request,
        "skill_ledger/skill_ledger_advisory.html",
        {
            "advisory_rows": template_rows,
            "safety_wording": REQUIRED_SKILL_ADVISORY_SAFETY_WORDING,
            "jd_signal_safety_wording": REQUIRED_JD_SIGNAL_SAFETY_WORDING,
            "classifications": ADVISORY_CLASSIFICATIONS,
            "has_jd_candidate_terms": bool(jd_candidate_terms),
        },
    )


@login_required
@require_GET
def skill_ledger_advisory_explanations(request):
    entries = SkillEntry.objects.for_user(request.user).order_by(
        "evidence_level",
        "category",
        "skill_name",
    )
    jd_candidate_terms = collect_jd_candidate_terms(request.user)
    advisory_rows = build_skill_advisory_rows(entries, jd_candidate_terms=jd_candidate_terms)
    explanations = build_skill_advisory_explanations(advisory_rows)
    explanation_rows = tuple(explanation_to_dict(explanation) for explanation in explanations)
    return render(
        request,
        "skill_ledger/skill_advisory_explanations.html",
        {
            "explanation_rows": explanation_rows,
            "required_explanation_safety_warning": REQUIRED_EXPLANATION_SAFETY_WARNING,
            "provider_mode": SPRINT_87_PROVIDER_MODE_MOCKED,
            "jd_signal_safety_wording": REQUIRED_JD_SIGNAL_SAFETY_WORDING,
            "skill_advisory_safety_wording": REQUIRED_SKILL_ADVISORY_SAFETY_WORDING,
        },
    )


@login_required
@require_GET
def skill_ledger_advisory_ai_evidence(request):
    owned_entries = SkillEntry.objects.for_user(request.user)
    entries = owned_entries.order_by("evidence_level", "category", "skill_name")
    skill_entry_count = owned_entries.count()
    jd_candidate_terms = collect_jd_candidate_terms(request.user)
    advisory_rows = build_skill_advisory_rows(entries, jd_candidate_terms=jd_candidate_terms)
    advisory_row_count = len(advisory_rows)
    return render(
        request,
        "skill_ledger/skill_advisory_ai_evidence.html",
        {
            "provider_mode": SPRINT_87_PROVIDER_MODE_MOCKED,
            "required_explanation_safety_warning": REQUIRED_EXPLANATION_SAFETY_WARNING,
            "jd_signal_safety_wording": REQUIRED_JD_SIGNAL_SAFETY_WORDING,
            "skill_advisory_safety_wording": REQUIRED_SKILL_ADVISORY_SAFETY_WORDING,
            "system_status": {
                "Provider mode": SPRINT_87_PROVIDER_MODE_MOCKED,
                "Live provider configured": "No",
                "API key configured": "No",
                "Raw provider output stored": "No",
                "Raw JD text rendered": "No",
                "Mutation/save/update": "No",
            },
            "contract_health": {
                "Required safety warning": "Present",
                "Forbidden phrase count": len(FORBIDDEN_EXPLANATION_PHRASES),
                "Schema frozen": "Yes",
                "Golden cases": 8,
            },
            "data_counts": {
                "Skill Ledger entries": skill_entry_count,
                "Advisory rows generated": advisory_row_count,
                "JD signal context terms": len(jd_candidate_terms),
                "Explanation rows available": advisory_row_count,
            },
            "boundary_summary": {
                "Public exposure": "No",
                "Auto apply": "No",
                "CV/profile mutation": "No",
                "Background task": "No",
            },
        },
    )


@login_required
@require_GET
def skill_ledger_advisory_ai_review_hub(request):
    owned_entries = SkillEntry.objects.for_user(request.user)
    entries = owned_entries.order_by("evidence_level", "category", "skill_name")
    jd_candidate_terms = collect_jd_candidate_terms(request.user)
    advisory_rows = build_skill_advisory_rows(entries, jd_candidate_terms=jd_candidate_terms)
    explanations = build_skill_advisory_explanations(advisory_rows)
    return render(
        request,
        "skill_ledger/skill_advisory_ai_review_hub.html",
        {
            "explanation_preview_url": "/skill-ledger/advisory/explanations/",
            "safety_evidence_url": "/skill-ledger/advisory/ai-evidence/",
            "required_explanation_safety_warning": REQUIRED_EXPLANATION_SAFETY_WARNING,
            "summary_strip": {
                "Skill Ledger entries": owned_entries.count(),
                "Advisory rows": len(advisory_rows),
                "Explanation rows": len(explanations),
                "Provider mode": SPRINT_87_PROVIDER_MODE_MOCKED,
            },
        },
    )


@login_required
@require_GET
def advisory_evaluation_casebook(request):
    evaluation_cases = [
        {
            "title": "Skill claim inflation check",
            "scenario": (
                "A planning note describes a learning target as if it were already backed by "
                "portfolio evidence."
            ),
            "evaluation_focus": "Keep skill claims tied to supplied evidence and manual review.",
            "safety_boundary": "Do not treat learning targets as verified skill proficiency.",
            "expected_safe_behaviour": (
                "Frame the skill as a learning priority until project evidence, tests, "
                "screenshots, or work experience support the claim."
            ),
            "fail_condition": (
                "The advisory wording presents the skill as proven, certified, or ready to "
                "claim without evidence."
            ),
        },
        {
            "title": "Live AI/provider claim check",
            "scenario": "A reviewer expects the page to show provider-backed advisory output.",
            "evaluation_focus": "Make the deterministic, no-provider boundary explicit.",
            "safety_boundary": "Do not imply live model execution or provider integration.",
            "expected_safe_behaviour": (
                "State that the examples are static planning cases and that no live AI model "
                "is used."
            ),
            "fail_condition": (
                "The page suggests provider-backed output, live evaluation, or model metrics."
            ),
        },
        {
            "title": "CV/public-profile mutation boundary",
            "scenario": "A case references CV or public profile wording after evidence review.",
            "evaluation_focus": "Separate private planning from public profile changes.",
            "safety_boundary": "Do not update CVs, LinkedIn, portfolios, or public profiles.",
            "expected_safe_behaviour": (
                "Ask for manual evidence review before any wording is used outside the private "
                "tracker."
            ),
            "fail_condition": (
                "The example says that a CV, LinkedIn profile, portfolio, or public profile was "
                "changed automatically."
            ),
        },
        {
            "title": "Application submission boundary",
            "scenario": "A planning case discusses whether a role needs a missing skill.",
            "evaluation_focus": "Keep advisory review separate from application actions.",
            "safety_boundary": "Do not submit, draft, or send applications from this page.",
            "expected_safe_behaviour": (
                "Explain that role decisions and application actions remain manual."
            ),
            "fail_condition": (
                "The example implies that an application was submitted, queued, or sent."
            ),
        },
        {
            "title": "Skill Ledger evidence escalation boundary",
            "scenario": "A Skill Ledger entry is listed as studying or no evidence.",
            "evaluation_focus": "Keep evidence levels manually maintained.",
            "safety_boundary": "Do not escalate Skill Ledger evidence from static examples.",
            "expected_safe_behaviour": (
                "Treat evidence status as a manual record that needs separate review before "
                "any claim changes."
            ),
            "fail_condition": (
                "The casebook implies that static review examples upgraded Skill Ledger "
                "evidence."
            ),
        },
        {
            "title": "Learning recommendation advisory boundary",
            "scenario": "A learning recommendation suggests practice for a missing skill.",
            "evaluation_focus": "Keep learning recommendations advisory and non-verifying.",
            "safety_boundary": "Do not present learning recommendations as proof of skill.",
            "expected_safe_behaviour": (
                "Describe the recommendation as a planning aid and require manual evidence "
                "before claiming the skill."
            ),
            "fail_condition": (
                "The case treats a recommendation as proof that the skill is ready to claim."
            ),
        },
        {
            "title": "JD signal advisory boundary",
            "scenario": "A job description mentions a skill that is missing from the ledger.",
            "evaluation_focus": "Keep JD signals separate from proficiency claims.",
            "safety_boundary": "Do not treat JD mentions as evidence of user proficiency.",
            "expected_safe_behaviour": (
                "Use the JD signal as a learning or evidence-gathering prompt only."
            ),
            "fail_condition": (
                "The case suggests that a JD mention proves the user has the skill."
            ),
        },
        {
            "title": "Generated document boundary",
            "scenario": "A reviewer asks whether the casebook creates finished career documents.",
            "evaluation_focus": "Separate static review examples from document creation.",
            "safety_boundary": "Do not create CVs, cover letters, profiles, or applications.",
            "expected_safe_behaviour": (
                "Keep examples as private planning references with no generated documents."
            ),
            "fail_condition": (
                "The page presents a finished CV, cover letter, profile, or application."
            ),
        },
    ]
    return render(
        request,
        "skill_ledger/skill_advisory_evaluation_casebook.html",
        {"evaluation_cases": evaluation_cases},
    )


@login_required
@require_GET
def skill_ledger_advisory_manual_review_checklist(request):
    return render(
        request,
        "skill_ledger/skill_advisory_manual_review_checklist.html",
    )


@login_required
@require_http_methods(["GET", "POST"])
def skill_ledger_rag_result(request):
    """Minimal authenticated Skill Ledger RAG result surface (Sprint 119 Phase 3).

    Production provider is always None (fail closed). Tests may call the
    generation service with an injected ExplanationProvider.
    """
    query = ""
    retrieved = ()
    validated_result = None
    error_code = None
    form_submitted = False

    if request.method == "POST":
        form_submitted = True
        query = str(request.POST.get("q", "") or "").strip()
        if not query:
            error_code = RagRejectionCode.INVALID_QUERY
        elif len(query) > QUERY_MAX_LEN:
            error_code = RagRejectionCode.INVALID_QUERY
        else:
            try:
                embedding_provider = DeterministicOfflineEmbeddingProvider()
                retrieved = retrieve_owned_skill_evidence(
                    request.user,
                    query,
                    provider=embedding_provider,
                )
            except EvidenceRetrievalError:
                error_code = RagRejectionCode.PROVIDER_ERROR
                retrieved = ()
            else:
                # Production: no compatible RAG composer exists. Fail closed.
                generation = generate_grounded_rag_answer(
                    query,
                    retrieved,
                    provider=None,
                )
                if generation.ok:
                    validated_result = generation.validated
                else:
                    error_code = generation.code

    return render(
        request,
        "skill_ledger/rag_result.html",
        {
            "query": query,
            "form_submitted": form_submitted,
            "retrieved": retrieved,
            "error_code": error_code,
            "validated_result": validated_result,
        },
    )


@login_required
def skill_entry_detail(request, pk):
    entry = get_object_or_404(SkillEntry.objects.for_user(request.user), pk=pk)
    return render(
        request,
        "skill_ledger/skill_entry_detail.html",
        {"entry": entry},
    )


@login_required
def skill_entry_edit(request, pk):
    entry = get_object_or_404(SkillEntry.objects.for_user(request.user), pk=pk)
    if request.method == "POST":
        form = SkillEntryForm(request.POST, instance=entry)
        if form.is_valid():
            entry = form.save()
            messages.success(
                request,
                "Skill entry updated. Your private Skill Ledger record has been saved.",
            )
            return redirect("skill_ledger:detail", pk=entry.pk)
    else:
        form = SkillEntryForm(instance=entry)

    return render(
        request,
        "skill_ledger/skill_entry_form.html",
        {"form": form, "entry": entry, "is_edit": True},
    )


@login_required
def skill_entry_create(request):
    if request.method == "POST":
        form = SkillEntryForm(request.POST)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.user = request.user
            entry.save()
            return redirect("skill_ledger:detail", pk=entry.pk)
    else:
        form = SkillEntryForm()

    return render(
        request,
        "skill_ledger/skill_entry_form.html",
        {"form": form, "is_edit": False},
    )
