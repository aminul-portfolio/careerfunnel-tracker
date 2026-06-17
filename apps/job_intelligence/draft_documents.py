from __future__ import annotations

import re
from dataclasses import dataclass

from apps.ai_agents.services import analyze_job_posting, normalise_text
from apps.applications.choices import DocumentSource, DocumentStatus, DocumentType
from apps.applications.models import ApplicationDocument, JobApplication
from apps.job_intelligence.constants import GOOD_SKILLS, LEARNING_TARGETS, TARGET_TITLES_AE_STRETCH
from apps.job_intelligence.services import LOCKED_CV, SmartApplicationReview, build_smart_review

MASTER_CV_BASELINE = LOCKED_CV
MASTER_CV_HEADLINE = (
    "Data Analyst | BI Analyst | Junior Analytics Engineer | "
    "Python, SQL, Excel, Django, dbt, DuckDB | FX & FinTech Operations"
)

DEFAULT_PROJECT_ORDER = (
    "BakeOps Intelligence",
    "CareerFunnel Tracker",
    "TradeIntel 360",
    "DataBridge Market API / MarketVista Dashboard",
    "bakeops-dbt",
)

CAREERFUNNEL_EVIDENCE = (
    "CareerFunnel Tracker demonstrates a Django/Python analytics workflow with "
    "structured application records, funnel-stage metrics, source-performance reporting, "
    "data-quality warnings, manual intake workflow, skill-gap tracking, application "
    "readiness checks, and Application Document Pack workflow for storing/referencing "
    "externally generated CV and cover-letter documents, backed by 900+ validated "
    "tests."
)

BAKEOPS_EVIDENCE = (
    "BakeOps Intelligence demonstrates KPI reporting, BI-ready exports, data-quality "
    "thinking, and a rank-inversion insight where revenue rank and waste-adjusted "
    "margin rank diverge."
)

TRADEINTEL_EVIDENCE = (
    "TradeIntel 360 demonstrates FinTech trading analytics with risk/reward, "
    "drawdown, expectancy, session-level analysis, and CSV-based reporting."
)

DATABRIDGE_EVIDENCE = (
    "DataBridge Market API / MarketVista Dashboard demonstrates API ingestion, market "
    "data monitoring, ETL-style thinking, dashboard-ready data, watchlists, and "
    "alert-style signals for analyst visibility."
)

BAKEOPS_DBT_EVIDENCE = (
    "bakeops-dbt demonstrates dbt Core and DuckDB portfolio analytics-engineering "
    "evidence through bakeops-dbt, with 7 models and 26 dbt tests - not "
    "production or cloud warehouse deployment."
)

PROJECT_EVIDENCE = {
    "BakeOps Intelligence": BAKEOPS_EVIDENCE,
    "CareerFunnel Tracker": CAREERFUNNEL_EVIDENCE,
    "TradeIntel 360": TRADEINTEL_EVIDENCE,
    "DataBridge Market API / MarketVista Dashboard": DATABRIDGE_EVIDENCE,
    "bakeops-dbt": BAKEOPS_DBT_EVIDENCE,
}

DRAFT_HELPER_TEXT = (
    "Draft only. Review manually before using in an application. "
    "Saved records remain draft text only - review manually before use."
)

JOB_POSTING_SAVE_HELPER_TEXT = (
    "To save these drafts, first create or open an application record, "
    "then use Application Smart Review."
)

COVER_LETTER_DISCLAIMER = (
    "Draft Cover Letter - review before use."
)


@dataclass(frozen=True)
class CVTailoringDraft:
    recommended_cv_filename: str
    master_cv_baseline: str
    headline: str
    profile_angle: str
    skills_to_prioritise: tuple[str, ...]
    project_evidence: tuple[str, ...]
    work_experience_angle: str
    learning_gaps: tuple[str, ...]
    claim_safety_warnings: tuple[str, ...]


@dataclass(frozen=True)
class ApplicationDocumentDrafts:
    cv_tailoring: CVTailoringDraft
    cover_letter_draft: str
    cover_letter_disclaimer: str
    claim_safety_notes: tuple[str, ...]
    recommended_project_evidence: tuple[str, ...]
    helper_text: str


def _sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "_", (value or "").strip())
    cleaned = cleaned.strip("_")
    return cleaned or "Role"


def _display_or_fallback(value: str, fallback: str = "Not specified") -> str:
    return value.strip() if value and value.strip() else fallback


def _combined_job_text(
    *,
    company_name: str = "",
    job_title: str = "",
    location: str = "",
    job_description: str = "",
    required_skills: str = "",
) -> str:
    return normalise_text(
        company_name,
        job_title,
        location,
        job_description,
        required_skills,
    )


def _build_recommended_cv_filename(company_name: str, job_title: str) -> str:
    company_part = _sanitize_filename_part(company_name)
    role_part = _sanitize_filename_part(job_title)
    return f"{MASTER_CV_BASELINE}_{company_part}_{role_part}"


def _detect_profile_angle(text: str) -> str:
    if any(title in text for title in TARGET_TITLES_AE_STRETCH) and any(
        word in text for word in ["etl", "pipeline", "api", "data product", "dbt", "duckdb"]
    ):
        return (
            "Junior Analytics Engineer stretch angle - emphasise bakeops-dbt portfolio "
            "dbt/DuckDB evidence, Python, SQL, and ETL-style project work, but keep "
            "primary positioning as Data Analyst / BI Analyst."
        )
    if any(word in text for word in ["bi", "dashboard", "power bi", "reporting", "insights"]):
        return (
            "BI Analyst angle - emphasise KPI dashboards, reporting outputs, metric "
            "definitions, and stakeholder-ready summaries."
        )
    if any(word in text for word in ["finance", "fx", "fintech", "reconciliation", "ledger"]):
        return (
            "Data Analyst with finance / FX / FinTech operations angle - emphasise "
            "operational reporting accuracy, reconciliation discipline, and KPI insight."
        )
    return (
        "Data Analyst / BI Analyst angle - emphasise Python, SQL, Excel, Django, and "
        "evidence-based analytics workflow delivery."
    )


def _prioritise_projects(text: str, suggested: list[str]) -> tuple[str, ...]:
    priority_keys: list[tuple[str, ...]] = [
        ("finance", "fx", "fintech", "trading", "market", "risk"),
        ("operations", "kpi", "margin", "waste"),
        ("dbt", "duckdb", "data modelling", "data modeling", "analytics engineer"),
        ("etl", "api", "pipeline", "integration"),
    ]
    project_sets = [
        ("TradeIntel 360", "DataBridge Market API / MarketVista Dashboard", "BakeOps Intelligence"),
        ("BakeOps Intelligence", "CareerFunnel Tracker", "TradeIntel 360"),
        ("bakeops-dbt", "DataBridge Market API / MarketVista Dashboard", "CareerFunnel Tracker"),
        ("DataBridge Market API / MarketVista Dashboard", "TradeIntel 360", "CareerFunnel Tracker"),
    ]
    ordered: list[str] = []
    for keys, projects in zip(priority_keys, project_sets, strict=False):
        if any(key in text for key in keys):
            ordered.extend(projects)
            break
    if not ordered:
        ordered.extend(DEFAULT_PROJECT_ORDER)
    for project in suggested:
        if project not in ordered:
            ordered.append(project)
    for project in DEFAULT_PROJECT_ORDER:
        if project not in ordered:
            ordered.append(project)
    deduped: list[str] = []
    for project in ordered:
        if project not in deduped:
            deduped.append(project)
    return tuple(deduped[:4])


def _skills_to_prioritise(text: str, matched_skills: list[str]) -> tuple[str, ...]:
    skills = matched_skills or [skill for skill in GOOD_SKILLS if skill in text]
    if not skills:
        return ("Python", "SQL", "Excel", "Django", "reporting")
    return tuple(skills[:8])


def _learning_gaps(text: str) -> tuple[str, ...]:
    gaps = [target for target in LEARNING_TARGETS if target in text]
    if gaps:
        return tuple(sorted(set(gaps)))
    return ("Not enough evidence from the job analysis",)


def _work_experience_angle(text: str) -> str:
    if any(word in text for word in ["finance", "fx", "reconciliation", "ledger", "operations"]):
        return (
            "Highlight FX and FinTech operations experience, reconciliation discipline, "
            "and stakeholder reporting in operational analytics contexts."
        )
    return (
        "Highlight finance / FX / operational reporting background where relevant, "
        "keeping claims aligned to documented experience."
    )


def _build_claim_safety_notes(
    *,
    learning_gaps: tuple[str, ...],
    text: str,
) -> tuple[str, ...]:
    notes = [
        (
            "Draft CV Tailoring Notes and Draft Cover Letter are advisory only. "
            "Review manually before use."
        ),
        "Do not present draft text as a final CV or final cover letter.",
        "Keep claims evidence-based and portfolio-scope only - portfolio project only.",
        "Rule-based generation only - no external AI/API calls were used for these drafts.",
    ]
    if learning_gaps and learning_gaps[0] != "Not enough evidence from the job analysis":
        notes.append(
            "Job analysis mentions tools outside strong portfolio evidence. "
            "Review manually before use and avoid unsupported tool claims."
        )
    if any(word in text for word in TARGET_TITLES_AE_STRETCH):
        notes.append(
            "Analytics Engineer positioning is a stretch angle only unless the role clearly "
            "supports it."
        )
    return tuple(notes)


def _build_cv_claim_safety_warnings(learning_gaps: tuple[str, ...]) -> tuple[str, ...]:
    warnings = [
        "Use the locked master CV baseline only - do not invent alternate CV filenames.",
        "Review before use - draft download only; not a final CV.",
    ]
    if learning_gaps and learning_gaps[0] != "Not enough evidence from the job analysis":
        warnings.append(
            "Mention learning gaps carefully; do not claim production experience "
            "with unsupported tools."
        )
    return tuple(warnings)


def _project_evidence_lines(projects: tuple[str, ...]) -> tuple[str, ...]:
    lines: list[str] = []
    for project in projects:
        fallback = f"{project} - review project evidence manually."
        lines.append(PROJECT_EVIDENCE.get(project, fallback))
    return tuple(lines)


def _learning_gap_sentence(gaps: tuple[str, ...]) -> str:
    relevant = [gap for gap in gaps if gap != "Not enough evidence from the job analysis"]
    if not relevant:
        return ""
    tool = relevant[0]
    return (
        f"I am currently building familiarity with {tool} through project-based learning."
    )


def _build_cover_letter_draft(
    *,
    company_name: str,
    job_title: str,
    location: str,
    matched_skills: tuple[str, ...],
    learning_gaps: tuple[str, ...],
    projects: tuple[str, ...],
) -> str:
    company = _display_or_fallback(company_name)
    role = _display_or_fallback(job_title)
    location_text = _display_or_fallback(location, "Not specified")
    del matched_skills  # CV tailoring notes only; not echoed in employer-facing draft letter

    paragraph_1 = (
        f"I am writing to express my interest in the {role} role at {company}. "
        f"The posting aligns with my target path in data and reporting analytics, "
        f"and I would welcome the opportunity to contribute in a {location_text} context."
    )
    if company == "Not specified" or role == "Not specified":
        paragraph_1 = (
            "I am writing to express my interest in this data and reporting analytics role. "
            "Review the company and role details manually before use."
        )

    paragraph_2 = (
        "My background includes finance, FX, and operational reporting work where accuracy, "
        "reconciliation discipline, and clear KPI communication matter. I focus on "
        "evidence-based analysis that helps stakeholders understand performance and next steps."
    )

    project_lines = []
    if "BakeOps Intelligence" in projects:
        project_lines.append(BAKEOPS_EVIDENCE)
    if "CareerFunnel Tracker" in projects:
        project_lines.append(CAREERFUNNEL_EVIDENCE)
    if not project_lines:
        project_lines.append(
            "Not enough evidence from the job analysis - "
            "review project evidence manually before use."
        )
    paragraph_3 = " ".join(project_lines)

    paragraph_4 = (
        "The role highlights several reporting and analytics requirements. I can connect "
        "the strongest matched requirements to documented portfolio work and manual, "
        "claim-safe workflow discipline."
    )
    learning_sentence = _learning_gap_sentence(learning_gaps)
    if learning_sentence:
        paragraph_4 = f"{paragraph_4} {learning_sentence}"

    paragraph_5 = (
        f"Thank you for reviewing my application for the {role} opportunity at {company}. "
        "I would welcome a conversation about how my analytics workflow and project evidence "
        "could support your team. Review before use."
    )
    if company == "Not specified" or role == "Not specified":
        paragraph_5 = (
            "Thank you for reviewing my application. I would welcome a conversation about how "
            "my analytics workflow and project evidence could support your team. Review before use."
        )

    return "\n\n".join(
        [
            paragraph_1,
            paragraph_2,
            paragraph_3,
            paragraph_4,
            paragraph_5,
        ]
    )


def build_application_document_drafts_from_fields(
    *,
    company_name: str = "",
    job_title: str = "",
    location: str = "",
    job_description: str = "",
    required_skills: str = "",
    fit_score: int | None = None,
    fit_label: str = "",
    recommended_cv: str = "",
    recommended_projects: list[str] | None = None,
    readiness_missing: list[str] | None = None,
) -> ApplicationDocumentDrafts:
    text = _combined_job_text(
        company_name=company_name,
        job_title=job_title,
        location=location,
        job_description=job_description,
        required_skills=required_skills,
    )
    analysis = analyze_job_posting(
        company_name=company_name,
        job_title=job_title,
        location=location,
        job_posting=" ".join(
            part for part in (job_description, required_skills) if part
        ),
    )
    matched_skills = tuple(_skills_to_prioritise(text, analysis.matched_skills))
    projects = _prioritise_projects(text, recommended_projects or analysis.recommended_projects)
    learning_gaps = _learning_gaps(text)
    claim_safety_notes = _build_claim_safety_notes(learning_gaps=learning_gaps, text=text)

    cv_tailoring = CVTailoringDraft(
        recommended_cv_filename=_build_recommended_cv_filename(company_name, job_title),
        master_cv_baseline=recommended_cv or analysis.recommended_cv or MASTER_CV_BASELINE,
        headline=MASTER_CV_HEADLINE,
        profile_angle=_detect_profile_angle(text),
        skills_to_prioritise=matched_skills,
        project_evidence=_project_evidence_lines(projects),
        work_experience_angle=_work_experience_angle(text),
        learning_gaps=learning_gaps,
        claim_safety_warnings=_build_cv_claim_safety_warnings(learning_gaps),
    )

    cover_letter = _build_cover_letter_draft(
        company_name=company_name,
        job_title=job_title,
        location=location,
        matched_skills=matched_skills,
        learning_gaps=learning_gaps,
        projects=projects,
    )

    if fit_score is None:
        fit_score = analysis.fit_score
    if not fit_label:
        fit_label = analysis.recommendation

    extra_notes = list(claim_safety_notes)
    if readiness_missing:
        extra_notes.append(
            "Application readiness gaps remain: "
            + "; ".join(readiness_missing[:4])
            + ". Review manually before use."
        )
    if fit_score < 40:
        extra_notes.append(
            "Fit score is low. Review manually before investing time in tailoring."
        )
    elif fit_label:
        extra_notes.append(f"Fit signal from job analysis: {fit_label}.")

    return ApplicationDocumentDrafts(
        cv_tailoring=cv_tailoring,
        cover_letter_draft=cover_letter,
        cover_letter_disclaimer=COVER_LETTER_DISCLAIMER,
        claim_safety_notes=tuple(extra_notes),
        recommended_project_evidence=_project_evidence_lines(projects),
        helper_text=DRAFT_HELPER_TEXT,
    )


def build_application_document_drafts(
    application: JobApplication,
    review: SmartApplicationReview | None = None,
) -> ApplicationDocumentDrafts:
    review = review or build_smart_review(application)
    return build_application_document_drafts_from_fields(
        company_name=application.company_name,
        job_title=application.job_title,
        location=application.location,
        job_description=application.job_description,
        required_skills=application.required_skills,
        fit_score=review.job_fit_score,
        fit_label=review.job_fit_label,
        recommended_cv=review.recommended_cv,
        recommended_projects=list(review.recommended_projects),
        readiness_missing=list(review.readiness_missing_items),
    )


def _join_text_lines(lines: tuple[str, ...] | list[str]) -> str:
    return "\n".join(line for line in lines if line)


def _build_cover_letter_filename(company_name: str, job_title: str) -> str:
    company_part = _sanitize_filename_part(company_name)
    if not (company_name or "").strip():
        company_part = "Not_Specified"
    role_part = _sanitize_filename_part(job_title)
    return f"Aminul_Islam_Cover_Letter_{company_part}_{role_part}"


def _render_cv_content(drafts: ApplicationDocumentDrafts) -> str:
    cv = drafts.cv_tailoring
    return _join_text_lines(
        [
            "Draft CV Tailoring Notes",
            f"Headline / positioning: {cv.headline}",
            f"Recommended CV title / file name: {cv.recommended_cv_filename}",
            f"Master CV baseline: {cv.master_cv_baseline}",
            "",
            f"Profile angle: {cv.profile_angle}",
            "",
            "Skills to prioritise:",
            *[f"- {skill}" for skill in cv.skills_to_prioritise],
            "",
            "Project evidence to emphasise:",
            *[f"- {item}" for item in cv.project_evidence],
            "",
            f"Work experience angle: {cv.work_experience_angle}",
            "",
            "Learning gaps to mention carefully:",
            *[f"- {gap}" for gap in cv.learning_gaps],
        ]
    )


def _render_cv_tailoring_notes(drafts: ApplicationDocumentDrafts) -> str:
    cv = drafts.cv_tailoring
    return _join_text_lines(
        [
            f"Profile angle: {cv.profile_angle}",
            "",
            "Skills to prioritise:",
            *[f"- {skill}" for skill in cv.skills_to_prioritise],
            "",
            f"Work experience angle: {cv.work_experience_angle}",
            "",
            "Learning gaps to mention carefully:",
            *[f"- {gap}" for gap in cv.learning_gaps],
        ]
    )


def _render_claim_safety_notes(drafts: ApplicationDocumentDrafts) -> str:
    combined = list(drafts.cv_tailoring.claim_safety_warnings) + list(drafts.claim_safety_notes)
    return _join_text_lines(combined)


def _render_project_evidence(drafts: ApplicationDocumentDrafts) -> str:
    return _join_text_lines(drafts.recommended_project_evidence)


def _render_quick_call_notes(
    application: JobApplication,
    drafts: ApplicationDocumentDrafts,
) -> str:
    cover_letter_name = _build_cover_letter_filename(
        application.company_name,
        application.job_title,
    )
    return _join_text_lines(
        [
            f"Company: {_display_or_fallback(application.company_name)}",
            f"Role: {_display_or_fallback(application.job_title)}",
            f"CV draft name: {drafts.cv_tailoring.recommended_cv_filename}",
            f"Cover letter draft name: {cover_letter_name}",
            "Review saved draft records manually before any company call.",
        ]
    )


def _sanitize_employer_cover_letter_body(
    body: str,
    *,
    company_name: str = "",
    job_title: str = "",
) -> str:
    from apps.applications.master_cv import sanitize_cover_letter_body

    cleaned = sanitize_cover_letter_body(
        body,
        company_name=company_name,
        job_title=job_title,
    )
    paragraphs: list[str] = []
    for part in cleaned.split("\n\n"):
        text = part.strip()
        if not text:
            continue
        lowered = text.lower()
        if "828 automated tests" in lowered:
            continue
        text = re.sub(r"\s*review before use\.?\s*", "", text, flags=re.IGNORECASE).strip()
        if text and "828 automated tests" not in text.lower():
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def build_complete_cv_content(
    application: JobApplication,
    drafts: ApplicationDocumentDrafts,
) -> str:
    """Return employer-facing master CV plain text for professional export."""
    del application
    from apps.applications.master_cv import (
        build_structured_master_cv,
        structured_document_to_plain_text,
    )

    cv = drafts.cv_tailoring
    structured = build_structured_master_cv(
        profile_angle=cv.profile_angle,
        skills_to_prioritise=cv.skills_to_prioritise,
    )
    return structured_document_to_plain_text(structured)


def build_clean_cover_letter_content(
    *,
    company_name: str,
    job_title: str,
    body: str,
) -> str:
    """Return employer-facing cover letter plain text with standard letter structure."""
    from apps.applications.master_cv import (
        build_structured_cover_letter,
        structured_document_to_plain_text,
    )

    cleaned_body = _sanitize_employer_cover_letter_body(
        body,
        company_name=company_name,
        job_title=job_title,
    )
    structured = build_structured_cover_letter(
        company_name=company_name,
        job_title=job_title,
        body=cleaned_body,
    )
    return structured_document_to_plain_text(structured)


def build_draft_cv_notes_download_text(drafts: ApplicationDocumentDrafts) -> str:
    """Plain text for draft CV tailoring notes download (advisory only)."""
    return _join_text_lines(
        [
            "Draft only - review manually before use.",
            "",
            _render_cv_content(drafts),
        ]
    )


def build_draft_cover_letter_download_text(drafts: ApplicationDocumentDrafts) -> str:
    """Plain text for draft cover letter download (advisory only)."""
    return _join_text_lines(
        [
            drafts.cover_letter_disclaimer,
            "Draft only - review manually before use.",
            "",
            drafts.cover_letter_draft,
        ]
    )


def build_draft_application_pack_download_text(drafts: ApplicationDocumentDrafts) -> str:
    """Plain text for combined draft application pack download (advisory only)."""
    return _join_text_lines(
        [
            "Draft Application Pack",
            "Draft only - review manually before use.",
            "",
            build_draft_cv_notes_download_text(drafts),
            "",
            "Draft Cover Letter",
            drafts.cover_letter_disclaimer,
            "",
            drafts.cover_letter_draft,
            "",
            "Claim-Safety Notes",
            _render_claim_safety_notes(drafts),
        ]
    )


def build_analyzer_draft_download_filename(
    prefix: str,
    company_name: str,
    job_title: str,
    extension: str,
) -> str:
    from django.utils import timezone

    from apps.applications.file_storage import build_safe_generated_filename, sanitize_filename_part

    company = sanitize_filename_part(company_name, fallback="Company")
    role = sanitize_filename_part(job_title, fallback="Role")
    date_suffix = timezone.localdate().strftime("%Y%m%d")
    base = f"{prefix}_{company}_{role}_{date_suffix}"
    return build_safe_generated_filename(base, extension)


DRAFT_CV_NOTES_FILENAME_PREFIX = "Aminul_Islam_Draft_CV_Notes"
DRAFT_COVER_LETTER_FILENAME_PREFIX = "Aminul_Islam_Draft_Cover_Letter"
DRAFT_APPLICATION_PACK_FILENAME_PREFIX = "Aminul_Islam_Draft_Application_Pack"


def render_analyzer_draft_download_bytes(text: str, file_format: str) -> bytes:
    from apps.applications.professional_exports import render_application_pack_bytes

    normalized = (file_format or "pdf").lower()
    if normalized not in {"pdf", "docx"}:
        normalized = "pdf"
    return render_application_pack_bytes(text, normalized)


def save_application_document_drafts(
    application: JobApplication,
    drafts: ApplicationDocumentDrafts,
) -> tuple[ApplicationDocument, ApplicationDocument]:
    """Persist generated draft text as two ApplicationDocument records."""
    cv_document = ApplicationDocument.objects.create(
        application=application,
        document_type=DocumentType.CV,
        name=drafts.cv_tailoring.recommended_cv_filename,
        status=DocumentStatus.DRAFT,
        source=DocumentSource.JOB_ANALYZER,
        content=_render_cv_content(drafts),
        tailoring_notes=_render_cv_tailoring_notes(drafts),
        project_evidence=_render_project_evidence(drafts),
        claim_safety_notes=_render_claim_safety_notes(drafts),
        quick_call_notes=_render_quick_call_notes(application, drafts),
        cv_baseline_name=drafts.cv_tailoring.master_cv_baseline,
    )
    cover_letter_document = ApplicationDocument.objects.create(
        application=application,
        document_type=DocumentType.COVER_LETTER,
        name=_build_cover_letter_filename(application.company_name, application.job_title),
        status=DocumentStatus.DRAFT,
        source=DocumentSource.JOB_ANALYZER,
        content=drafts.cover_letter_draft,
        tailoring_notes=_join_text_lines(
            [
                drafts.cover_letter_disclaimer,
                "Draft only - review manually before use.",
            ]
        ),
        project_evidence=_render_project_evidence(drafts),
        claim_safety_notes=_render_claim_safety_notes(drafts),
        quick_call_notes=_render_quick_call_notes(application, drafts),
        cv_baseline_name=drafts.cv_tailoring.master_cv_baseline,
    )
    return cv_document, cover_letter_document
