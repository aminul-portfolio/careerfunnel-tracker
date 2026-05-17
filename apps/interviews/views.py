from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.applications.services import build_application_evidence_readiness
from apps.job_intelligence.services import build_smart_review

from .forms import InterviewPrepForm
from .models import InterviewPrep


@login_required
def interview_list(request):
    interviews = InterviewPrep.objects.filter(user=request.user)
    return render(request, "interviews/interview_list.html", {"interviews": interviews})


@login_required
def interview_detail(request, pk):
    interview = get_object_or_404(InterviewPrep, pk=pk, user=request.user)
    return render(
        request,
        "interviews/interview_detail.html",
        {
            "interview": interview,
            "evidence_readiness": build_application_evidence_readiness(interview.application),
            "smart_review": build_smart_review(interview.application),
        },
    )


@login_required
def interview_create(request):
    if request.method == "POST":
        form = InterviewPrepForm(request.POST, user=request.user)
        if form.is_valid():
            interview = form.save(commit=False)
            interview.user = request.user
            interview.save()
            messages.success(request, "Interview prep created successfully.")
            return redirect(interview.get_absolute_url())
    else:
        form = InterviewPrepForm(user=request.user)
    return render(
        request,
        "interviews/interview_form.html",
        {
            "form": form,
            "page_title": "Add Interview Prep",
            "submit_label": "Save Interview Prep",
        },
    )


@login_required
def interview_update(request, pk):
    interview = get_object_or_404(InterviewPrep, pk=pk, user=request.user)
    if request.method == "POST":
        form = InterviewPrepForm(request.POST, instance=interview, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Interview prep updated successfully.")
            return redirect(interview.get_absolute_url())
    else:
        form = InterviewPrepForm(instance=interview, user=request.user)
    return render(
        request,
        "interviews/interview_form.html",
        {
            "form": form,
            "page_title": "Edit Interview Prep",
            "submit_label": "Update Interview Prep",
        },
    )


@login_required
def interview_delete(request, pk):
    interview = get_object_or_404(InterviewPrep, pk=pk, user=request.user)
    if request.method == "POST":
        interview.delete()
        messages.success(request, "Interview prep deleted successfully.")
        return redirect("interviews:interview_list")
    return render(request, "interviews/interview_confirm_delete.html", {"interview": interview})
