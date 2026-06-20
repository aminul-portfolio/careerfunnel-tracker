from django import forms
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

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
    entries = SkillEntry.objects.all().order_by("skill_name")
    return render(
        request,
        "skill_ledger/skill_ledger_list.html",
        {"entries": entries},
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
