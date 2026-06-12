from __future__ import annotations

from dataclasses import dataclass

from django.urls import reverse

from apps.applications import master_cv as master_cv_files
from apps.applications.choices import DEFAULT_CV_BASELINE_NAME, DocumentType
from apps.applications.document_exports import (
    render_application_document_docx,
    render_application_document_pdf,
)
from apps.applications.file_storage import (
    build_professional_application_pack_download_filename,
    build_professional_cover_letter_download_filename,
    build_professional_cv_download_filename,
)
from apps.applications.models import ApplicationDocument, JobApplication
from apps.applications.professional_exports import render_application_pack_bytes
from apps.applications.services import (
    build_application_table_rows,
    display_evaluation_cv_label,
    export_cover_letter_version_label,
    export_cv_version_label,
)
from apps.job_intelligence.services import build_smart_review

MANUAL_REVIEW_NOTE = (
    "Draft/manual-review export from saved CareerFunnel Tracker records. "
    "Review before use. No automatic submission is performed."
)

COVER_LETTER_MISSING_MESSAGE = "No cover letter draft available yet"


@dataclass(frozen=True)
class EvaluationFormatUrls:
    pdf: str | None
    docx: str | None


@dataclass(frozen=True)
class EvaluationDownloadState:
    cv_available: bool
    cover_letter_available: bool
    cv_missing_message: str
    cover_letter_missing_message: str
    cv_urls: EvaluationFormatUrls | None
    cover_letter_urls: EvaluationFormatUrls | None
    application_pack_urls: EvaluationFormatUrls
    cv_version_display: str
    cover_letter_version_display: str


def _document_has_content(document: ApplicationDocument | None) -> bool:
    if document is None:
        return False
    return bool((document.content or "").strip())


def resolve_cv_document(application: JobApplication) -> ApplicationDocument | None:
    selected = getattr(application, "selected_cv_document", None)
    if _document_has_content(selected):
        return selected
    return (
        ApplicationDocument.objects.filter(
            application=application,
            document_type=DocumentType.CV,
        )
        .exclude(content="")
        .order_by("-updated_at")
        .first()
    )


def resolve_cover_letter_document(application: JobApplication) -> ApplicationDocument | None:
    selected = getattr(application, "selected_cover_letter_document", None)
    if _document_has_content(selected):
        return selected
    return (
        ApplicationDocument.objects.filter(
            application=application,
            document_type=DocumentType.COVER_LETTER,
        )
        .exclude(content="")
        .order_by("-updated_at")
        .first()
    )


def build_evaluation_download_filename(
    prefix: str,
    application: JobApplication,
    extension: str,
) -> str:
    reference_date = application.date_applied
    builders = {
        "cv": build_professional_cv_download_filename,
        "cover_letter": build_professional_cover_letter_download_filename,
        "application_pack": build_professional_application_pack_download_filename,
    }
    builder = builders.get(prefix)
    if builder is None:
        raise ValueError(f"Unsupported evaluation download prefix: {prefix}")
    return builder(
        application.company_name,
        application.job_title,
        extension,
        download_date=reference_date,
    )


def render_evaluation_cv_pdf(application: JobApplication) -> bytes:
    document = resolve_cv_document(application)
    if document is None:
        raise ValueError(master_cv_files.CV_MISSING_MESSAGE)
    return render_application_document_pdf(document)


def render_evaluation_cv_docx(application: JobApplication) -> bytes:
    document = resolve_cv_document(application)
    if document is None:
        raise ValueError(master_cv_files.CV_MISSING_MESSAGE)
    return render_application_document_docx(document)


def render_evaluation_cover_letter_pdf(application: JobApplication) -> bytes:
    document = resolve_cover_letter_document(application)
    if document is None:
        raise ValueError("No cover letter document available.")
    return render_application_document_pdf(document)


def render_evaluation_cover_letter_docx(application: JobApplication) -> bytes:
    document = resolve_cover_letter_document(application)
    if document is None:
        raise ValueError("No cover letter document available.")
    return render_application_document_docx(document)


def build_evaluation_application_pack_text(application: JobApplication) -> str:
    smart_review = build_smart_review(application)
    cover_letter_document = resolve_cover_letter_document(application)

    if master_cv_files.any_master_cv_file_is_available():
        selected_cv_name = DEFAULT_CV_BASELINE_NAME
    elif resolve_cv_document(application) is not None:
        selected_cv_name = DEFAULT_CV_BASELINE_NAME
    elif application.cv_version:
        selected_cv_name = export_cv_version_label(application.cv_version)
    else:
        selected_cv_name = ""

    cover_letter_text = ""
    if cover_letter_document is not None:
        cover_letter_text = cover_letter_document.content or ""
    elif application.cover_letter_version:
        cover_letter_label = export_cover_letter_version_label(
            application.cover_letter_version,
            application.company_name,
            application.job_title,
        )
        cover_letter_text = f"Cover letter version recorded: {cover_letter_label}"

    claim_safety_notes: list[str] = []
    if cover_letter_document and cover_letter_document.claim_safety_notes:
        claim_safety_notes.append(cover_letter_document.claim_safety_notes.strip())
    if not claim_safety_notes:
        claim_safety_notes.append(MANUAL_REVIEW_NOTE)

    project_lines = smart_review.recommended_projects or ["Not saved."]
    evidence_lines = [f"- {project}" for project in project_lines]

    lines = [
        "CareerFunnel Tracker Application Pack",
        "",
        MANUAL_REVIEW_NOTE,
        "",
        f"Company: {application.company_name or 'Not specified'}",
        f"Role title: {application.job_title or 'Not specified'}",
        f"Job URL: {application.job_url or 'Not saved'}",
        f"Fit score: {smart_review.job_fit_score}/100",
        f"Fit rating: {smart_review.job_fit_label}",
        f"Role fit: {application.get_role_fit_display()}",
        f"Pipeline stage: {application.get_pipeline_stage_display()}",
        f"Decision / next action: {smart_review.next_action}",
        "",
        f"Selected CV name/version: {selected_cv_name or master_cv_files.CV_MISSING_MESSAGE}",
        "",
        "Cover letter text",
        cover_letter_text or COVER_LETTER_MISSING_MESSAGE,
        "",
        "Best evidence / portfolio projects",
        *evidence_lines,
        "",
        "Claim-safety notes",
        *[f"- {note}" for note in claim_safety_notes],
    ]
    return "\n".join(lines)


def render_evaluation_application_pack_pdf(application: JobApplication) -> bytes:
    pack_text = build_evaluation_application_pack_text(application)
    return render_application_pack_bytes(pack_text, "pdf")


def render_evaluation_application_pack_docx(application: JobApplication) -> bytes:
    pack_text = build_evaluation_application_pack_text(application)
    return render_application_pack_bytes(pack_text, "docx")


def _build_format_urls(route_name: str, application_pk: int) -> EvaluationFormatUrls:
    return EvaluationFormatUrls(
        pdf=reverse(route_name, kwargs={"pk": application_pk, "file_format": "pdf"}),
        docx=reverse(route_name, kwargs={"pk": application_pk, "file_format": "docx"}),
    )


def _build_cv_format_urls(application_pk: int) -> EvaluationFormatUrls | None:
    application = JobApplication.objects.filter(pk=application_pk).first()
    if application is None or resolve_cv_document(application) is None:
        return None
    return _build_format_urls(
        "applications:evaluation_cv_download",
        application_pk,
    )


def build_evaluation_download_state(application: JobApplication) -> EvaluationDownloadState:
    cv_document = resolve_cv_document(application)
    cover_letter_document = resolve_cover_letter_document(application)
    cv_urls = _build_cv_format_urls(application.pk)
    cv_available = cv_document is not None
    cover_letter_available = cover_letter_document is not None
    cover_letter_version_display = export_cover_letter_version_label(
        application.cover_letter_version,
        application.company_name,
        application.job_title,
    )
    if not cover_letter_version_display and cover_letter_available:
        cover_letter_version_display = f"Draft cover letter - {application.company_name}"
    elif not cover_letter_version_display:
        cover_letter_version_display = COVER_LETTER_MISSING_MESSAGE

    return EvaluationDownloadState(
        cv_available=cv_available,
        cover_letter_available=cover_letter_available,
        cv_missing_message=master_cv_files.CV_MISSING_MESSAGE,
        cover_letter_missing_message=COVER_LETTER_MISSING_MESSAGE,
        cv_urls=cv_urls,
        cover_letter_urls=(
            _build_format_urls(
                "applications:evaluation_cover_letter_download",
                application.pk,
            )
            if cover_letter_available
            else None
        ),
        application_pack_urls=_build_format_urls(
            "applications:evaluation_application_pack_download",
            application.pk,
        ),
        cv_version_display=display_evaluation_cv_label(
            application=application,
            cv_document_available=cv_available,
        ),
        cover_letter_version_display=cover_letter_version_display,
    )


def build_evaluation_queue_rows(applications):
    rows = []
    for table_row in build_application_table_rows(applications):
        application = table_row["application"]
        rows.append(
            {
                **table_row,
                "downloads": build_evaluation_download_state(application),
            }
        )
    return rows
