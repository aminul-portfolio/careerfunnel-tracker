from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.ai_agents.services import (
    ANALYZER_BORDERLINE_FIT_MIN_SCORE,
    ANALYZER_STRONG_FIT_MIN_SCORE,
)
from apps.followups.services import build_followup_email_draft, mark_followup_sent
from apps.job_intelligence.services import build_smart_review

from .choices import (
    DEFAULT_CV_BASELINE_NAME,
    ApplicationStatus,
    DocumentType,
    PipelineStage,
    RoleFit,
)
from .document_exports import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    build_application_document_download_filename,
    render_application_document_download_bytes,
)
from .document_uploads import attach_document_pack_upload, attach_external_reference
from .evaluation_downloads import (
    build_evaluation_download_filename,
    build_evaluation_queue_rows,
    render_evaluation_application_pack_docx,
    render_evaluation_application_pack_pdf,
    render_evaluation_cover_letter_docx,
    render_evaluation_cover_letter_pdf,
    render_evaluation_cv_docx,
    render_evaluation_cv_pdf,
)
from .forms import (
    ApplicationDocumentSelectionForm,
    DocumentPackUploadForm,
    ExternalDocumentReferenceForm,
    JobApplicationForm,
)
from .models import ApplicationDocument, JobApplication
from .selectors import get_user_applications
from .services import (
    build_analyzer_cv_version_display,
    build_application_cv_version_display,
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
    applications = (
        get_user_applications(request.user)
        .filter(
            pipeline_stage__in=[PipelineStage.JOB_FOUND, PipelineStage.FIT_CHECKED],
        )
        .select_related(
            "selected_cv_document",
            "selected_cover_letter_document",
        )
        .order_by("-date_applied", "-pk")
    )
    return render(
        request,
        "applications/evaluation_queue.html",
        {
            "applications": applications,
            "table_rows": build_evaluation_queue_rows(applications),
        },
    )


@login_required
def evaluation_cv_download(request, pk, file_format):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    normalized_format = file_format.lower()
    try:
        if normalized_format == "pdf":
            content = render_evaluation_cv_pdf(application)
            content_type = PDF_CONTENT_TYPE
        elif normalized_format == "docx":
            content = render_evaluation_cv_docx(application)
            content_type = DOCX_CONTENT_TYPE
        else:
            raise Http404("Unsupported download format.")
    except ValueError as exc:
        raise Http404(str(exc)) from exc
    filename = build_evaluation_download_filename(
        "cv",
        application,
        normalized_format,
    )
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def evaluation_cover_letter_download(request, pk, file_format):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    normalized_format = file_format.lower()
    try:
        if normalized_format == "pdf":
            content = render_evaluation_cover_letter_pdf(application)
            content_type = PDF_CONTENT_TYPE
        elif normalized_format == "docx":
            content = render_evaluation_cover_letter_docx(application)
            content_type = DOCX_CONTENT_TYPE
        else:
            raise Http404("Unsupported download format.")
    except ValueError as exc:
        raise Http404(str(exc)) from exc
    filename = build_evaluation_download_filename(
        "cover_letter",
        application,
        normalized_format,
    )
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def evaluation_application_pack_download(request, pk, file_format):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    normalized_format = file_format.lower()
    if normalized_format == "pdf":
        content = render_evaluation_application_pack_pdf(application)
        content_type = PDF_CONTENT_TYPE
    elif normalized_format == "docx":
        content = render_evaluation_application_pack_docx(application)
        content_type = DOCX_CONTENT_TYPE
    else:
        raise Http404("Unsupported download format.")
    filename = build_evaluation_download_filename(
        "application_pack",
        application,
        normalized_format,
    )
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def application_detail(request, pk):
    application = get_object_or_404(
        JobApplication.objects.select_related(
            "selected_cv_document",
            "selected_cover_letter_document",
        ),
        pk=pk,
        user=request.user,
    )
    document_selection_form = ApplicationDocumentSelectionForm(
        application=application,
        initial={
            "selected_cv_document": application.selected_cv_document_id,
            "selected_cover_letter_document": application.selected_cover_letter_document_id,
        },
    )
    external_cv_form = ExternalDocumentReferenceForm(prefix="external_cv")
    external_cover_letter_form = ExternalDocumentReferenceForm(prefix="external_cl")
    upload_cv_form = DocumentPackUploadForm(prefix="upload_cv")
    upload_cover_letter_form = DocumentPackUploadForm(prefix="upload_cl")

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "select_documents":
            document_selection_form = ApplicationDocumentSelectionForm(
                request.POST,
                application=application,
            )
            if document_selection_form.is_valid():
                application.selected_cv_document = document_selection_form.cleaned_data[
                    "selected_cv_document"
                ]
                application.selected_cover_letter_document = document_selection_form.cleaned_data[
                    "selected_cover_letter_document"
                ]
                application.save(
                    update_fields=[
                        "selected_cv_document",
                        "selected_cover_letter_document",
                        "updated_at",
                    ]
                )
                messages.success(
                    request,
                    "Selected CV and cover letter updated for this application.",
                )
                return redirect(f"{application.get_absolute_url()}#document-pack")
        elif action == "create_external_cv":
            external_cv_form = ExternalDocumentReferenceForm(
                request.POST,
                prefix="external_cv",
            )
            if external_cv_form.is_valid():
                attach_external_reference(
                    application=application,
                    document_type=DocumentType.CV,
                    name=external_cv_form.cleaned_data["name"],
                    notes=external_cv_form.cleaned_data.get("notes", ""),
                )
                messages.success(
                    request,
                    "External CV reference saved for manual evidence tracking.",
                )
                return redirect(f"{application.get_absolute_url()}#document-pack")
        elif action == "create_external_cover_letter":
            external_cover_letter_form = ExternalDocumentReferenceForm(
                request.POST,
                prefix="external_cl",
            )
            if external_cover_letter_form.is_valid():
                attach_external_reference(
                    application=application,
                    document_type=DocumentType.COVER_LETTER,
                    name=external_cover_letter_form.cleaned_data["name"],
                    notes=external_cover_letter_form.cleaned_data.get("notes", ""),
                )
                messages.success(
                    request,
                    "External cover letter reference saved for manual evidence tracking.",
                )
                return redirect(f"{application.get_absolute_url()}#document-pack")
        elif action == "upload_cv":
            upload_cv_form = DocumentPackUploadForm(
                request.POST,
                request.FILES,
                prefix="upload_cv",
            )
            if upload_cv_form.is_valid():
                result = attach_document_pack_upload(
                    application=application,
                    document_type=DocumentType.CV,
                    uploaded_file=upload_cv_form.cleaned_data["uploaded_file"],
                )
                messages.success(request, result.message)
                return redirect(f"{application.get_absolute_url()}#document-pack")
        elif action == "upload_cover_letter":
            upload_cover_letter_form = DocumentPackUploadForm(
                request.POST,
                request.FILES,
                prefix="upload_cl",
            )
            if upload_cover_letter_form.is_valid():
                result = attach_document_pack_upload(
                    application=application,
                    document_type=DocumentType.COVER_LETTER,
                    uploaded_file=upload_cover_letter_form.cleaned_data["uploaded_file"],
                )
                messages.success(request, result.message)
                return redirect(f"{application.get_absolute_url()}#document-pack")

    quick_call_notes = _build_quick_call_review_notes(application)
    return render(
        request,
        "applications/application_detail.html",
        {
            "application": application,
            "badge_class": get_status_badge_class(application.status),
            "followup_email_draft": build_followup_email_draft(application),
            "evidence_readiness": build_application_evidence_readiness(application),
            "smart_review": build_smart_review(application),
            "cv_version_display": build_application_cv_version_display(application),
            "document_selection_form": document_selection_form,
            "external_cv_form": external_cv_form,
            "external_cover_letter_form": external_cover_letter_form,
            "upload_cv_form": upload_cv_form,
            "upload_cover_letter_form": upload_cover_letter_form,
            "quick_call_notes": quick_call_notes,
        },
    )


def _build_quick_call_review_notes(application: JobApplication) -> str:
    notes: list[str] = []
    if application.selected_cv_document and application.selected_cv_document.quick_call_notes:
        notes.append(application.selected_cv_document.quick_call_notes)
    if (
        application.selected_cover_letter_document
        and application.selected_cover_letter_document.quick_call_notes
        and application.selected_cover_letter_document != application.selected_cv_document
    ):
        notes.append(application.selected_cover_letter_document.quick_call_notes)
    if notes:
        return "\n\n".join(notes)
    return "No quick call notes saved on selected documents yet."


@login_required
def application_document_download(request, pk, document_pk, file_format):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    document = get_object_or_404(
        ApplicationDocument.objects.select_related("application"),
        pk=document_pk,
        application=application,
    )
    normalized_format = file_format.lower()
    try:
        content = render_application_document_download_bytes(document, normalized_format)
        if normalized_format == "docx":
            content_type = DOCX_CONTENT_TYPE
        elif normalized_format == "pdf":
            content_type = PDF_CONTENT_TYPE
        else:
            raise Http404("Unsupported download format.")
    except ValueError as exc:
        raise Http404(str(exc)) from exc
    filename = build_application_document_download_filename(document, normalized_format)
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def application_mark_followup_sent(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    mark_followup_sent(application)
    messages.success(request, "Follow-up marked as sent.")
    return redirect(application.get_absolute_url())


def _application_create_prefill_params(request):
    return ("company_name", "job_title", "location", "fit_score")


def _has_application_create_prefill(request) -> bool:
    return any(key in request.GET for key in _application_create_prefill_params(request))


def _build_application_create_initial(request):
    initial: dict[str, str] = {}
    has_prefill = _has_application_create_prefill(request)

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
                if fit_score >= ANALYZER_STRONG_FIT_MIN_SCORE:
                    initial["role_fit"] = RoleFit.STRONG
                elif fit_score >= ANALYZER_BORDERLINE_FIT_MIN_SCORE:
                    initial["role_fit"] = RoleFit.MEDIUM
                else:
                    initial["role_fit"] = RoleFit.WEAK

    if has_prefill:
        initial["status"] = ApplicationStatus.SAVED_FOR_LATER
        initial["pipeline_stage"] = PipelineStage.FIT_CHECKED
        initial["cv_version"] = DEFAULT_CV_BASELINE_NAME

    return initial


@login_required
def application_create(request):
    is_analyzer_prefill = _has_application_create_prefill(request)
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
            "is_analyzer_prefill": is_analyzer_prefill,
            "cv_version_display": build_analyzer_cv_version_display(
                company_name=form["company_name"].value() or "",
                job_title=form["job_title"].value() or "",
            ),
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
            "cv_version_display": build_application_cv_version_display(application),
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
