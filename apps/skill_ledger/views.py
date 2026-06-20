from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET

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
def skill_entry_detail(request, pk):
    entry = get_object_or_404(SkillEntry, pk=pk)
    return render(
        request,
        "skill_ledger/skill_entry_detail.html",
        {"entry": entry},
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
        {"form": form},
    )
