from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.followups.services import build_followup_email_draft, mark_followup_sent

from .forms import JobApplicationForm
from .models import JobApplication
from .selectors import get_user_applications
from .services import (
    build_application_evidence_readiness,
    build_application_summary,
    build_application_table_rows,
    calculate_interview_rate,
    calculate_offer_rate,
    calculate_response_rate,
    get_status_badge_class,
)


@login_required
def application_list(request):
    applications = get_user_applications(request.user)
    status_filter = request.GET.get("status")
    search_query = request.GET.get("q")

    if status_filter:
        applications = applications.filter(status=status_filter)
    if search_query:
        applications = applications.filter(
            Q(company_name__icontains=search_query)
            | Q(job_title__icontains=search_query),
        )

    context = {
        "applications": applications,
        "table_rows": build_application_table_rows(applications),
        "summary": build_application_summary(request.user),
        "response_rate": calculate_response_rate(request.user),
        "interview_rate": calculate_interview_rate(request.user),
        "offer_rate": calculate_offer_rate(request.user),
        "status_filter": status_filter,
        "search_query": search_query or "",
    }
    return render(request, "applications/application_list.html", context)


@login_required
def application_detail(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    return render(
        request,
        "applications/application_detail.html",
        {
            "application": application,
            "badge_class": get_status_badge_class(application.status),
            "followup_email_draft": build_followup_email_draft(application),
            "evidence_readiness": build_application_evidence_readiness(application),
        },
    )


@login_required
@require_POST
def application_mark_followup_sent(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    mark_followup_sent(application)
    messages.success(request, "Follow-up marked as sent.")
    return redirect(application.get_absolute_url())


@login_required
def application_create(request):
    if request.method == "POST":
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            messages.success(request, "Application added successfully.")
            return redirect(application.get_absolute_url())
    else:
        form = JobApplicationForm()
    return render(
        request,
        "applications/application_form.html",
        {
            "form": form,
            "page_title": "Add Application",
            "submit_label": "Save Application",
        },
    )


@login_required
def application_update(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    if request.method == "POST":
        form = JobApplicationForm(request.POST, instance=application)
        if form.is_valid():
            form.save()
            messages.success(request, "Application updated successfully.")
            return redirect(application.get_absolute_url())
    else:
        form = JobApplicationForm(instance=application)
    return render(
        request,
        "applications/application_form.html",
        {
            "form": form,
            "page_title": "Edit Application",
            "submit_label": "Update Application",
            "application": application,
        },
    )


@login_required
def application_delete(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    if request.method == "POST":
        application.delete()
        messages.success(request, "Application deleted successfully.")
        return redirect("applications:application_list")
    return render(
        request,
        "applications/application_confirm_delete.html",
        {"application": application},
    )
