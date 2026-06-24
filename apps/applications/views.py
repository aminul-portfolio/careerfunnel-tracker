from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

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
    ApplicationStatusUpdateForm,
    DocumentPackUploadForm,
    ExternalDocumentReferenceForm,
    JobApplicationForm,
)
from .models import ApplicationDocument, JobApplication
from .selectors import get_user_applications
from .services import (
    append_status_note,
    build_analyzer_cv_version_display,
    build_application_cv_version_display,
    build_application_evidence_readiness,
    build_application_summary,
    build_application_table_rows,
    build_jd_gap_aggregation_context,
    build_save_quality_warnings,
    calculate_interview_rate,
    calculate_offer_rate,
    calculate_response_rate,
    get_status_badge_class,
)

JD_READY_TEXT_THRESHOLD = 750


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
@require_GET
def application_data_quality_audit(request):
    applications = list(
        JobApplication.objects.filter(user=request.user).order_by("-date_applied", "-pk"),
    )
    context = _build_application_data_quality_context(applications)
    return render(request, "applications/data_quality_audit.html", context)


@login_required
@require_GET
def jd_gap_aggregation(request):
    context = build_jd_gap_aggregation_context(request.user)
    return render(
        request,
        "applications/jd_gap_aggregation.html",
        {"aggregation": context},
    )


def _clean_application_value(value) -> str:
    return (value or "").strip()


def _audit_percentage(present_count: int, total_records: int) -> int:
    if total_records == 0:
        return 0
    return round((present_count / total_records) * 100)


def _build_field_completeness_row(label: str, present_count: int, total_records: int) -> dict:
    return {
        "label": label,
        "present": present_count,
        "missing": total_records - present_count,
        "percent_complete": _audit_percentage(present_count, total_records),
    }


def _build_application_data_quality_context(applications: list[JobApplication]) -> dict:
    total_records = len(applications)
    url_counts: dict[str, int] = {}
    company_title_counts: dict[tuple[str, str], int] = {}

    cleaned_records = []
    for application in applications:
        company_name = _clean_application_value(application.company_name)
        job_title = _clean_application_value(application.job_title)
        location = _clean_application_value(application.location)
        job_url = _clean_application_value(application.job_url)
        job_description = _clean_application_value(application.job_description)
        company_title_key = (company_name, job_title)

        if job_url:
            url_counts[job_url] = url_counts.get(job_url, 0) + 1
        if company_name and job_title:
            company_title_counts[company_title_key] = (
                company_title_counts.get(company_title_key, 0) + 1
            )

        cleaned_records.append(
            {
                "application": application,
                "company_name": company_name,
                "job_title": job_title,
                "location": location,
                "job_url": job_url,
                "job_description": job_description,
                "jd_text_length": len(job_description),
                "company_title_key": company_title_key,
            },
        )

    duplicate_urls = {job_url for job_url, count in url_counts.items() if count > 1}
    duplicate_company_titles = {
        key for key, count in company_title_counts.items() if count > 1
    }

    jd_ready_records = []
    attention_records = []
    complete_records_count = 0
    missing_jd_text_count = 0
    possible_duplicate_url_record_count = 0
    company_title_duplicate_record_count = 0

    field_present_counts = {
        "company": 0,
        "job_title": 0,
        "location": 0,
        "source_url": 0,
        "jd_text": 0,
        "jd_text_sufficient": 0,
    }

    for record in cleaned_records:
        company_present = bool(record["company_name"])
        job_title_present = bool(record["job_title"])
        location_present = bool(record["location"])
        source_url_present = bool(record["job_url"])
        jd_text_present = bool(record["job_description"])
        jd_text_sufficient = record["jd_text_length"] >= JD_READY_TEXT_THRESHOLD
        possible_duplicate_url = record["job_url"] in duplicate_urls if record["job_url"] else False
        company_title_duplicate = (
            record["company_title_key"] in duplicate_company_titles
            if company_present and job_title_present
            else False
        )

        field_present_counts["company"] += int(company_present)
        field_present_counts["job_title"] += int(job_title_present)
        field_present_counts["location"] += int(location_present)
        field_present_counts["source_url"] += int(source_url_present)
        field_present_counts["jd_text"] += int(jd_text_present)
        field_present_counts["jd_text_sufficient"] += int(jd_text_sufficient)

        complete_records_count += int(
            company_present
            and job_title_present
            and location_present
            and source_url_present
            and jd_text_present,
        )
        missing_jd_text_count += int(not jd_text_present)
        possible_duplicate_url_record_count += int(possible_duplicate_url)
        company_title_duplicate_record_count += int(company_title_duplicate)

        row = {
            "company_name": record["company_name"] or "Missing company",
            "job_title": record["job_title"] or "Missing job title",
            "job_url": record["job_url"],
            "date_applied": record["application"].date_applied,
            "jd_text_length": record["jd_text_length"],
            "possible_duplicate_url": possible_duplicate_url,
            "company_title_duplicate": company_title_duplicate,
            "missing_fields": [],
        }

        if not company_present:
            row["missing_fields"].append("Company")
        if not job_title_present:
            row["missing_fields"].append("Job title")
        if not jd_text_present:
            row["missing_fields"].append("JD text")
        elif not jd_text_sufficient:
            row["missing_fields"].append("JD text >= 750 chars")

        is_jd_ready = (
            company_present
            and job_title_present
            and jd_text_present
            and jd_text_sufficient
            and not possible_duplicate_url
        )
        if is_jd_ready:
            jd_ready_records.append(row)
        else:
            attention_records.append(row)

    field_completeness_rows = [
        _build_field_completeness_row(
            "Company",
            field_present_counts["company"],
            total_records,
        ),
        _build_field_completeness_row(
            "Job title",
            field_present_counts["job_title"],
            total_records,
        ),
        _build_field_completeness_row(
            "Location",
            field_present_counts["location"],
            total_records,
        ),
        _build_field_completeness_row(
            "Source URL",
            field_present_counts["source_url"],
            total_records,
        ),
        _build_field_completeness_row(
            "JD text",
            field_present_counts["jd_text"],
            total_records,
        ),
        _build_field_completeness_row(
            "JD text >= 750 chars",
            field_present_counts["jd_text_sufficient"],
            total_records,
        ),
    ]

    jd_ready_count = len(jd_ready_records)
    completeness_rate = _audit_percentage(jd_ready_count, total_records)

    return {
        "total_records": total_records,
        "jd_ready_count": jd_ready_count,
        "missing_jd_text_count": missing_jd_text_count,
        "complete_records_count": complete_records_count,
        "possible_duplicate_url_record_count": possible_duplicate_url_record_count,
        "company_title_duplicate_record_count": company_title_duplicate_record_count,
        "completeness_rate": completeness_rate,
        "field_completeness_rows": field_completeness_rows,
        "jd_ready_records": jd_ready_records,
        "attention_records": attention_records,
        "jd_ready_text_threshold": JD_READY_TEXT_THRESHOLD,
    }


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
def application_status_update(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    if request.method == "POST":
        form = ApplicationStatusUpdateForm(request.POST, instance=application)
        if form.is_valid():
            updated_application = form.save(commit=False)
            updated_application.notes = append_status_note(
                application.notes,
                form.cleaned_data.get("status_note", ""),
                form.cleaned_data["status"],
            )
            updated_application.save(
                update_fields=[
                    "status",
                    "pipeline_stage",
                    "response_date",
                    "notes",
                    "updated_at",
                ],
            )
            messages.success(
                request,
                "Tracking status updated. Your CareerFunnel record has been saved.",
            )
            return redirect(application.get_absolute_url())
    else:
        form = ApplicationStatusUpdateForm(instance=application)
    return render(
        request,
        "applications/application_status_update.html",
        {
            "application": application,
            "form": form,
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
