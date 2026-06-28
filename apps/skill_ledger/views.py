from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

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
from .models import SkillEntry


class SkillEntryForm(forms.ModelForm):
    class Meta:
        model = SkillEntry
        fields = [
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
        ]
        help_texts = {
            "evidence_level": (
                "VERIFIED means portfolio evidence exists in a closed sprint, passing tests, "
                "or prior work experience - not external certification."
            ),
        }


@login_required
def skill_ledger_list(request):
    search_query = request.GET.get("q", "").strip()
    all_entries = SkillEntry.objects.all()
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
    public_entries = SkillEntry.objects.filter(
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
    entries = SkillEntry.objects.all().order_by("evidence_level", "category", "skill_name")
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
    entries = SkillEntry.objects.all().order_by("evidence_level", "category", "skill_name")
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
    entries = SkillEntry.objects.all().order_by("evidence_level", "category", "skill_name")
    skill_entry_count = SkillEntry.objects.count()
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
def skill_entry_detail(request, pk):
    entry = get_object_or_404(SkillEntry, pk=pk)
    return render(
        request,
        "skill_ledger/skill_entry_detail.html",
        {"entry": entry},
    )


@login_required
def skill_entry_edit(request, pk):
    entry = get_object_or_404(SkillEntry, pk=pk)
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
            entry = form.save()
            return redirect("skill_ledger:detail", pk=entry.pk)
    else:
        form = SkillEntryForm()

    return render(
        request,
        "skill_ledger/skill_entry_form.html",
        {"form": form, "is_edit": False},
    )
