from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.followups.services import build_followup_email_draft, mark_followup_sent
from apps.job_intelligence.services import build_smart_review

from .choices import PipelineStage, RoleFit
from .forms import JobApplicationForm
from .models import JobApplication
from .selectors import get_user_applications
from .services import (
    build_application_evidence_readiness,
    build_application_summary,
    build_application_table_rows,
    build_save_quality_warnings,
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
def evaluation_queue(request):
    applications = get_user_applications(request.user).filter(
        pipeline_stage__in=[PipelineStage.JOB_FOUND, PipelineStage.FIT_CHECKED],
    )
    return render(
        request,
        "applications/evaluation_queue.html",
        {
            "applications": applications,
            "table_rows": build_application_table_rows(applications),
        },
    )


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
            "smart_review": build_smart_review(application),
        },
    )


@login_required
@require_POST
def application_mark_followup_sent(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    mark_followup_sent(application)
    messages.success(request, "Follow-up marked as sent.")
    return redirect(application.get_absolute_url())


def _application_create_prefill_params(request):
    return ("company_name", "job_title", "location", "fit_score")


def _build_application_create_initial(request):
    initial: dict[str, str] = {}
    prefill_keys = _application_create_prefill_params(request)
    has_prefill = any(key in request.GET for key in prefill_keys)

    if "company_name" in request.GET:
        initial["company_name"] = request.GET.get("company_name", "")
    if "job_title" in request.GET:
        initial["job_title"] = request.GET.get("job_title", "")
    if "location" in request.GET:
        initial["location"] = request.GET.get("location", "")

    if "fit_score" in request.GET:
        fit_score_raw = request.GET.get("fit_score", "")
        if fit_score_raw != "":
            try:
                fit_score = int(fit_score_raw)
            except (TypeError, ValueError):
                pass
            else:
                if fit_score >= 60:
                    initial["role_fit"] = RoleFit.STRONG
                elif fit_score >= 40:
                    initial["role_fit"] = RoleFit.MEDIUM
                else:
                    initial["role_fit"] = RoleFit.WEAK

    if has_prefill:
        initial["pipeline_stage"] = PipelineStage.FIT_CHECKED

    return initial


@login_required
def application_create(request):
    if request.method == "POST":
        form = JobApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            for warning in build_save_quality_warnings(application):
                messages.warning(request, warning.message)
            messages.success(request, "Application added successfully.")
            return redirect(application.get_absolute_url())
    else:
        form = JobApplicationForm(initial=_build_application_create_initial(request))
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
            for warning in build_save_quality_warnings(application):
                messages.warning(request, warning.message)
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
