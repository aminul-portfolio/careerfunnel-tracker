from __future__ import annotations

import re
from dataclasses import dataclass

from django.db.models import Count
from django.utils import timezone

from apps.skill_ledger.models import SkillEntry

from .choices import (
    DEFAULT_COVER_LETTER_DRAFT_LABEL,
    DEFAULT_CV_BASELINE_NAME,
    LEGACY_COVER_LETTER_VERSION_LABELS,
    LEGACY_CV_VERSION_LABELS,
    ApplicationSource,
    ApplicationStatus,
    DocumentSource,
    DocumentType,
    FollowUpStatus,
)
from .file_storage import build_professional_cv_basename
from .file_storage import sanitize_filename_part as _sanitize_filename_part
from .models import ApplicationDocument, JobApplication
from .selectors import get_user_applications

JD_READY_TEXT_THRESHOLD = 750
MIN_TERM_FREQUENCY = 2
STATUS_HISTORY_HEADER_RE = re.compile(
    r"^\[(\d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}) - Status: ([^\]\n]+)\]\s*",
    re.MULTILINE,
)

TRACKED_TERMS = (
    (
        "Analytics Engineering",
        (
            ("dbt", ("dbt", "data build tool")),
            ("airflow", ("airflow", "apache airflow")),
            ("spark", ("apache spark", "pyspark")),
            ("bigquery", ("bigquery", "big query")),
            ("snowflake", ("snowflake",)),
            ("databricks", ("databricks",)),
            ("redshift", ("redshift",)),
        ),
    ),
    (
        "Business Intelligence",
        (
            ("power bi", ("power bi", "powerbi")),
            ("tableau", ("tableau",)),
            ("looker", ("looker",)),
            ("ssrs", ("ssrs", "sql server reporting")),
            ("qlik", ("qlik", "qlikview", "qliksense")),
            ("microsoft fabric", ("microsoft fabric", "ms fabric")),
        ),
    ),
    (
        "Programming",
        (
            ("python", ("python",)),
            ("sql", ("sql", "t-sql", "pl/sql")),
            ("r", ("r programming", "rstudio")),
            ("excel", ("excel", "advanced excel")),
            ("pandas", ("pandas",)),
            ("numpy", ("numpy",)),
        ),
    ),
    (
        "Cloud Platform",
        (
            ("azure", ("azure", "microsoft azure")),
            ("aws", ("aws", "amazon web services")),
            ("gcp", ("gcp", "google cloud")),
        ),
    ),
    (
        "Data Engineering",
        (
            ("etl", ("etl", "elt", "extract transform load")),
            ("data warehouse", ("data warehouse", "data warehousing")),
            ("data lake", ("data lake", "data lakehouse")),
            ("kafka", ("kafka", "apache kafka")),
        ),
    ),
    (
        "Governance",
        (
            ("dimensional modelling", ("dimensional model", "star schema", "snowflake schema")),
            ("data governance", ("data governance",)),
            ("data quality", ("data quality",)),
        ),
    ),
    (
        "Domain / reporting",
        (
            ("stakeholder", ("stakeholder",)),
            ("dashboard", ("dashboard",)),
            ("kpi", ("kpi", "key performance indicator")),
            ("reporting", ("reporting", "report writing")),
            ("data storytelling", ("data storytelling", "data narrative")),
        ),
    ),
)


def append_status_note(existing_notes: str, status_note: str, status: str) -> str:
    clean_note = (status_note or "").strip()
    if not clean_note:
        return existing_notes or ""

    timestamp = timezone.localtime(timezone.now()).strftime("%d %b %Y %H:%M")
    status_display = dict(ApplicationStatus.choices).get(status, status)
    note_block = f"[{timestamp} - Status: {status_display}]\n{clean_note}"
    clean_existing = (existing_notes or "").strip()
    if not clean_existing:
        return note_block
    return f"{clean_existing}\n\n{note_block}"


@dataclass(frozen=True)
class StatusHistoryEntry:
    timestamp: str
    status: str
    note: str


def parse_status_history(notes_text: str | None) -> list[StatusHistoryEntry]:
    notes = (notes_text or "").strip()
    if not notes:
        return []

    matches = list(STATUS_HISTORY_HEADER_RE.finditer(notes))
    if not matches:
        return []

    entries: list[StatusHistoryEntry] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(notes)
        entries.append(
            StatusHistoryEntry(
                timestamp=match.group(1).strip(),
                status=match.group(2).strip(),
                note=notes[match.end() : next_start].strip(),
            ),
        )
    return list(reversed(entries))


@dataclass(frozen=True)
class JdGapSampleApplication:
    company_name: str
    job_title: str
    date_applied: object


@dataclass(frozen=True)
class AggregatedTrackedTerm:
    term: str
    category: str
    frequency: int
    sample_applications: tuple[JdGapSampleApplication, ...]
    skill_ledger_match: SkillEntry | None = None
    skill_ledger_status: str = "Not in your skill ledger"
    skill_ledger_display: str = "Not in your skill ledger"
    is_verified: bool = False
    is_unmatched: bool = True


@dataclass(frozen=True)
class JdGapCategoryGroup:
    category: str
    terms: tuple[AggregatedTrackedTerm, ...]


@dataclass(frozen=True)
class JdGapAggregationContext:
    jd_ready_count: int
    terms_found_count: int
    top_term: AggregatedTrackedTerm | None
    unmatched_in_ledger_count: int
    category_groups: tuple[JdGapCategoryGroup, ...]
    unmatched_terms: tuple[AggregatedTrackedTerm, ...]
    verified_terms: tuple[AggregatedTrackedTerm, ...]
    min_term_frequency: int


def _clean_jd_gap_value(value: str | None) -> str:
    return (value or "").strip()


def get_jd_ready_applications_for_gap_aggregation(user) -> list[JobApplication]:
    applications = list(
        JobApplication.objects.filter(user=user).order_by("-date_applied", "-pk"),
    )
    url_counts: dict[str, int] = {}
    for application in applications:
        job_url = _clean_jd_gap_value(application.job_url)
        if job_url:
            url_counts[job_url] = url_counts.get(job_url, 0) + 1

    duplicate_urls = {job_url for job_url, count in url_counts.items() if count > 1}
    jd_ready_applications: list[JobApplication] = []
    for application in applications:
        company_name = _clean_jd_gap_value(application.company_name)
        job_title = _clean_jd_gap_value(application.job_title)
        job_description = _clean_jd_gap_value(application.job_description)
        job_url = _clean_jd_gap_value(application.job_url)
        if not company_name or not job_title or not job_description:
            continue
        if len(job_description) < JD_READY_TEXT_THRESHOLD:
            continue
        if job_url and job_url in duplicate_urls:
            continue
        jd_ready_applications.append(application)
    return jd_ready_applications


def _term_alias_is_present(description: str, alias: str) -> bool:
    pattern = rf"(?<!\w){re.escape(alias.lower())}(?!\w)"
    return re.search(pattern, description.lower()) is not None


def _application_mentions_term(application: JobApplication, aliases: tuple[str, ...]) -> bool:
    description = _clean_jd_gap_value(application.job_description)
    return any(_term_alias_is_present(description, alias) for alias in aliases)


def _build_jd_gap_sample(application: JobApplication) -> JdGapSampleApplication:
    return JdGapSampleApplication(
        company_name=_clean_jd_gap_value(application.company_name),
        job_title=_clean_jd_gap_value(application.job_title),
        date_applied=application.date_applied,
    )


def aggregate_tracked_jd_terms(
    applications: list[JobApplication],
) -> tuple[AggregatedTrackedTerm, ...]:
    aggregated_terms: list[AggregatedTrackedTerm] = []
    for category, term_group in TRACKED_TERMS:
        for term, aliases in term_group:
            matching_applications = [
                application
                for application in applications
                if _application_mentions_term(application, aliases)
            ]
            frequency = len(matching_applications)
            if frequency < MIN_TERM_FREQUENCY:
                continue
            aggregated_terms.append(
                AggregatedTrackedTerm(
                    term=term,
                    category=category,
                    frequency=frequency,
                    sample_applications=tuple(
                        _build_jd_gap_sample(application)
                        for application in matching_applications[:3]
                    ),
                ),
            )

    return tuple(
        sorted(
            aggregated_terms,
            key=lambda tracked_term: (
                -tracked_term.frequency,
                tracked_term.category,
                tracked_term.term,
            ),
        ),
    )


def _find_skill_ledger_match(term: str, skill_entries: list[SkillEntry]) -> SkillEntry | None:
    normalized_term = term.lower()
    for entry in skill_entries:
        if normalized_term in _clean_jd_gap_value(entry.skill_name).lower():
            return entry
    return None


def compare_aggregated_terms_with_skill_ledger(
    aggregated_terms: tuple[AggregatedTrackedTerm, ...],
) -> tuple[AggregatedTrackedTerm, ...]:
    skill_entries = list(SkillEntry.objects.all().order_by("skill_name", "pk"))
    compared_terms: list[AggregatedTrackedTerm] = []
    for aggregated_term in aggregated_terms:
        skill_entry = _find_skill_ledger_match(aggregated_term.term, skill_entries)
        if skill_entry is None:
            compared_terms.append(aggregated_term)
            continue
        skill_ledger_display = skill_entry.get_evidence_level_display()
        compared_terms.append(
            AggregatedTrackedTerm(
                term=aggregated_term.term,
                category=aggregated_term.category,
                frequency=aggregated_term.frequency,
                sample_applications=aggregated_term.sample_applications,
                skill_ledger_match=skill_entry,
                skill_ledger_status=f"Your skill ledger shows: {skill_ledger_display}",
                skill_ledger_display=skill_ledger_display,
                is_verified=skill_entry.evidence_level == SkillEntry.EvidenceLevel.VERIFIED,
                is_unmatched=False,
            ),
        )
    return tuple(compared_terms)


def _build_jd_gap_category_groups(
    aggregated_terms: tuple[AggregatedTrackedTerm, ...],
) -> tuple[JdGapCategoryGroup, ...]:
    groups: list[JdGapCategoryGroup] = []
    for category, _term_group in TRACKED_TERMS:
        category_terms = tuple(term for term in aggregated_terms if term.category == category)
        if category_terms:
            groups.append(JdGapCategoryGroup(category=category, terms=category_terms))
    return tuple(groups)


def build_jd_gap_aggregation_context(user) -> JdGapAggregationContext:
    jd_ready_applications = get_jd_ready_applications_for_gap_aggregation(user)
    aggregated_terms = aggregate_tracked_jd_terms(jd_ready_applications)
    compared_terms = compare_aggregated_terms_with_skill_ledger(aggregated_terms)
    unmatched_terms = tuple(term for term in compared_terms if term.is_unmatched)
    verified_terms = tuple(term for term in compared_terms if term.is_verified)
    return JdGapAggregationContext(
        jd_ready_count=len(jd_ready_applications),
        terms_found_count=len(compared_terms),
        top_term=compared_terms[0] if compared_terms else None,
        unmatched_in_ledger_count=len(unmatched_terms),
        category_groups=_build_jd_gap_category_groups(compared_terms),
        unmatched_terms=unmatched_terms,
        verified_terms=verified_terms,
        min_term_frequency=MIN_TERM_FREQUENCY,
    )


def export_cv_version_label(cv_version: str) -> str:
    cleaned = (cv_version or "").strip()
    if not cleaned:
        return ""
    return DEFAULT_CV_BASELINE_NAME


def resolve_application_cv_reference_date(application: JobApplication):
    return application.date_applied


def display_application_cv_version(
    *,
    company_name: str = "",
    job_title: str = "",
    reference_date=None,
) -> str:
    return build_professional_cv_basename(
        company_name,
        job_title,
        reference_date=reference_date,
    )


def display_application_cv_version_for_application(application: JobApplication) -> str:
    return build_professional_cv_basename(
        application.company_name,
        application.job_title,
        reference_date=resolve_application_cv_reference_date(application),
    )


def display_internal_cv_baseline(cv_version: str) -> str | None:
    cleaned = (cv_version or "").strip()
    if not cleaned:
        return None
    if cleaned in LEGACY_CV_VERSION_LABELS:
        return cleaned
    if cleaned == DEFAULT_CV_BASELINE_NAME:
        return cleaned
    return None


@dataclass(frozen=True)
class ApplicationCvVersionDisplay:
    professional_basename: str
    internal_baseline: str | None


def build_application_cv_version_display(
    application: JobApplication,
) -> ApplicationCvVersionDisplay:
    return ApplicationCvVersionDisplay(
        professional_basename=display_application_cv_version_for_application(application),
        internal_baseline=display_internal_cv_baseline(application.cv_version),
    )


def build_analyzer_cv_version_display(
    *,
    company_name: str = "",
    job_title: str = "",
    internal_cv: str = "",
) -> ApplicationCvVersionDisplay:
    return ApplicationCvVersionDisplay(
        professional_basename=display_application_cv_version(
            company_name=company_name,
            job_title=job_title,
        ),
        internal_baseline=display_internal_cv_baseline(internal_cv or DEFAULT_CV_BASELINE_NAME),
    )


def build_prefill_cover_letter_version_label(
    company_name: str,
    job_title: str,
) -> str:
    company = (company_name or "").strip()
    role = (job_title or "").strip()
    if company and role:
        company_part = _sanitize_filename_part(company)
        role_part = _sanitize_filename_part(role)
        return f"Aminul_Islam_Cover_Letter_{company_part}_{role_part}"
    return DEFAULT_COVER_LETTER_DRAFT_LABEL


def export_cover_letter_version_label(
    cover_letter_version: str,
    company_name: str = "",
    job_title: str = "",
) -> str:
    cleaned = (cover_letter_version or "").strip()
    if not cleaned:
        return ""
    if cleaned in LEGACY_COVER_LETTER_VERSION_LABELS:
        return build_prefill_cover_letter_version_label(company_name, job_title)
    return cleaned


def display_evaluation_cv_label(
    *,
    application: JobApplication,
    cv_document_available: bool,
) -> str:
    if not cv_document_available and not (application.cv_version or "").strip():
        return "No CV draft available yet"
    return display_application_cv_version_for_application(application)


@dataclass(frozen=True)
class ApplicationSummary:
    total_applications: int
    submitted_count: int
    acknowledged_count: int
    screening_call_count: int
    technical_screen_count: int
    interview_count: int
    offer_count: int
    rejected_count: int
    auto_rejected_count: int
    no_response_count: int


def build_application_summary(user) -> ApplicationSummary:
    applications = get_user_applications(user)
    status_counts = applications.values("status").annotate(total=Count("id"))
    count_map = {row["status"]: row["total"] for row in status_counts}
    return ApplicationSummary(
        total_applications=applications.count(),
        submitted_count=count_map.get(ApplicationStatus.SUBMITTED, 0),
        acknowledged_count=count_map.get(ApplicationStatus.ACKNOWLEDGED, 0),
        screening_call_count=count_map.get(ApplicationStatus.SCREENING_CALL, 0),
        technical_screen_count=count_map.get(ApplicationStatus.TECHNICAL_SCREEN, 0),
        interview_count=count_map.get(ApplicationStatus.INTERVIEW, 0),
        offer_count=count_map.get(ApplicationStatus.OFFER, 0),
        rejected_count=count_map.get(ApplicationStatus.REJECTED, 0),
        auto_rejected_count=count_map.get(ApplicationStatus.AUTO_REJECTED, 0),
        no_response_count=count_map.get(ApplicationStatus.NO_RESPONSE, 0),
    )


def calculate_response_rate(user) -> float:
    applications = get_user_applications(user)
    total = applications.count()
    if total == 0:
        return 0.0
    response_statuses = [
        ApplicationStatus.ACKNOWLEDGED,
        ApplicationStatus.SCREENING_CALL,
        ApplicationStatus.TECHNICAL_SCREEN,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.AUTO_REJECTED,
    ]
    response_count = applications.filter(status__in=response_statuses).count()
    return round((response_count / total) * 100, 2)


def calculate_interview_rate(user) -> float:
    applications = get_user_applications(user)
    total = applications.count()
    if total == 0:
        return 0.0
    interview_count = applications.filter(
        status__in=[ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER],
    ).count()
    return round((interview_count / total) * 100, 2)


def calculate_offer_rate(user) -> float:
    applications = get_user_applications(user)
    total = applications.count()
    if total == 0:
        return 0.0
    offer_count = applications.filter(status=ApplicationStatus.OFFER).count()
    return round((offer_count / total) * 100, 2)


def get_status_badge_class(status: str) -> str:
    status_map = {
        ApplicationStatus.SUBMITTED: "badge-neutral",
        ApplicationStatus.NO_RESPONSE: "badge-muted",
        ApplicationStatus.ACKNOWLEDGED: "badge-info",
        ApplicationStatus.SCREENING_CALL: "badge-primary",
        ApplicationStatus.TECHNICAL_SCREEN: "badge-warning",
        ApplicationStatus.INTERVIEW: "badge-warning",
        ApplicationStatus.OFFER: "badge-success",
        ApplicationStatus.REJECTED: "badge-danger",
        ApplicationStatus.AUTO_REJECTED: "badge-danger",
        ApplicationStatus.WITHDREW: "badge-muted",
    }
    return status_map.get(status, "badge-neutral")


def build_application_table_rows(applications):
    return [
        {
            "application": application,
            "badge_class": get_status_badge_class(application.status),
            "days_to_response": application.days_to_response,
        }
        for application in applications
    ]


READINESS_LABEL_STRONG = "Strong evidence"
READINESS_LABEL_NEEDS_IMPROVEMENT = "Needs improvement"
READINESS_LABEL_MISSING_KEY = "Missing key evidence"

ITEM_CV_VERSION = "CV version saved"
ITEM_COVER_LETTER_VERSION = "Cover letter version saved"
ITEM_JOB_URL = "Job URL saved"
ITEM_REQUIRED_SKILLS = "Required skills captured"
ITEM_JOB_DESCRIPTION = "Job description captured"
ITEM_CONTACT_EMAIL = "Contact email saved"
ITEM_COMPANY_RESEARCHED = "Company researched"
ITEM_PORTFOLIO_PROJECT = "Portfolio/project included"
ITEM_FOLLOW_UP_DATE = "Follow-up date set"
ITEM_FOLLOW_UP_STATUS = "Follow-up status known"

_KEY_EVIDENCE_ITEMS = frozenset(
    {
        ITEM_CV_VERSION,
        ITEM_COVER_LETTER_VERSION,
        ITEM_JOB_URL,
        ITEM_REQUIRED_SKILLS,
        ITEM_JOB_DESCRIPTION,
        ITEM_CONTACT_EMAIL,
    },
)

_EVIDENCE_CHECK_ORDER: tuple[tuple[str, str], ...] = (
    (ITEM_CV_VERSION, "Save the CV version used for this application."),
    (ITEM_COVER_LETTER_VERSION, "Save the cover letter version used for this application."),
    (
        ITEM_JOB_DESCRIPTION,
        "Capture the job description or key requirements (at least 40 characters).",
    ),
    (ITEM_REQUIRED_SKILLS, "Capture required skills from the posting (at least 10 characters)."),
    (ITEM_JOB_URL, "Save the job posting URL for quick reference and follow-up."),
    (ITEM_CONTACT_EMAIL, "Add a contact email so follow-up drafts have a recipient."),
    (
        ITEM_COMPANY_RESEARCHED,
        "Mark company research complete once you have reviewed the employer.",
    ),
    (ITEM_PORTFOLIO_PROJECT, "Note whether a portfolio project was included or referenced."),
    (ITEM_FOLLOW_UP_DATE, "Set a follow-up date to plan your next outreach."),
    (ITEM_FOLLOW_UP_STATUS, "Set follow-up status so the pipeline state is clear."),
)

_MIN_JOB_DESCRIPTION_CHARS = 40
_MIN_REQUIRED_SKILLS_CHARS = 10


@dataclass(frozen=True)
class ApplicationEvidenceReadiness:
    ready_items: tuple[str, ...]
    missing_items: tuple[str, ...]
    readiness_label: str
    recommended_next_improvement: str


def _strip_or_empty(value: str | None) -> str:
    if value is None:
        return ""
    return value.strip()


_GENERATED_DOCUMENT_SOURCES = frozenset(
    {
        DocumentSource.MANUAL,
        DocumentSource.JOB_ANALYZER,
        DocumentSource.MASTER_CV_BASELINE,
    }
)


def display_application_document_source(source: str) -> str:
    if source == DocumentSource.USER_UPLOAD:
        return "Manual upload"
    if source == DocumentSource.EXTERNAL_REFERENCE:
        return "External reference"
    if source in _GENERATED_DOCUMENT_SOURCES:
        return "Generated document"
    return "Generated document"


def _application_has_cv_evidence(application) -> bool:
    if application.selected_cv_document_id:
        return True
    if _strip_or_empty(application.cv_version) != "":
        return True
    return ApplicationDocument.objects.filter(
        application=application,
        document_type=DocumentType.CV,
    ).exists()


def _application_has_cover_letter_evidence(application) -> bool:
    if application.selected_cover_letter_document_id:
        return True
    if _strip_or_empty(application.cover_letter_version) != "":
        return True
    return ApplicationDocument.objects.filter(
        application=application,
        document_type=DocumentType.COVER_LETTER,
    ).exists()


def _has_cv_version(application) -> bool:
    return _application_has_cv_evidence(application)


def _has_cover_letter_version(application) -> bool:
    return _application_has_cover_letter_evidence(application)


def _has_job_url(application) -> bool:
    return _strip_or_empty(application.job_url) != ""


def _has_required_skills(application) -> bool:
    skills = _strip_or_empty(application.required_skills)
    return len(skills) >= _MIN_REQUIRED_SKILLS_CHARS


def _has_job_description(application) -> bool:
    description = _strip_or_empty(application.job_description)
    return len(description) >= _MIN_JOB_DESCRIPTION_CHARS


def _has_contact_email(application) -> bool:
    return _strip_or_empty(application.contact_email) != ""


def _has_follow_up_status(application) -> bool:
    return application.follow_up_status != FollowUpStatus.NOT_SET


def _collect_evidence_item_states(application) -> list[tuple[str, bool]]:
    return [
        (ITEM_CV_VERSION, _has_cv_version(application)),
        (ITEM_COVER_LETTER_VERSION, _has_cover_letter_version(application)),
        (ITEM_JOB_URL, _has_job_url(application)),
        (ITEM_REQUIRED_SKILLS, _has_required_skills(application)),
        (ITEM_JOB_DESCRIPTION, _has_job_description(application)),
        (ITEM_CONTACT_EMAIL, _has_contact_email(application)),
        (ITEM_COMPANY_RESEARCHED, application.company_researched),
        (ITEM_PORTFOLIO_PROJECT, application.portfolio_project_included),
        (ITEM_FOLLOW_UP_DATE, application.follow_up_date is not None),
        (ITEM_FOLLOW_UP_STATUS, _has_follow_up_status(application)),
    ]


def _determine_readiness_label(missing_items: tuple[str, ...]) -> str:
    if not missing_items:
        return READINESS_LABEL_STRONG
    missing_key_count = sum(1 for item in missing_items if item in _KEY_EVIDENCE_ITEMS)
    if missing_key_count >= 3 or len(missing_items) >= 6:
        return READINESS_LABEL_MISSING_KEY
    return READINESS_LABEL_NEEDS_IMPROVEMENT


def _recommended_next_improvement(missing_items: tuple[str, ...]) -> str:
    if not missing_items:
        return "Evidence is complete; keep records updated as the application progresses."
    missing_set = set(missing_items)
    for item_label, recommendation in _EVIDENCE_CHECK_ORDER:
        if item_label in missing_set:
            return recommendation
    return "Review and complete the remaining evidence items for this application."


def build_application_evidence_readiness(application) -> ApplicationEvidenceReadiness:
    item_states = _collect_evidence_item_states(application)
    ready_items = tuple(label for label, is_ready in item_states if is_ready)
    missing_items = tuple(label for label, is_ready in item_states if not is_ready)
    return ApplicationEvidenceReadiness(
        ready_items=ready_items,
        missing_items=missing_items,
        readiness_label=_determine_readiness_label(missing_items),
        recommended_next_improvement=_recommended_next_improvement(missing_items),
    )


_SAVE_QUALITY_SEVERITY_CRITICAL = "critical"
_SAVE_QUALITY_SEVERITY_IMPORTANT = "important"


@dataclass(frozen=True)
class SaveQualityWarning:
    field_name: str
    message: str
    analytics_impact: str
    severity: str


def build_save_quality_warnings(application) -> list[SaveQualityWarning]:
    warnings: list[SaveQualityWarning] = []

    if application.source == ApplicationSource.OTHER.value:
        warnings.append(
            SaveQualityWarning(
                field_name="source",
                message=(
                    "Source is set to the generic 'Other' - Source ROI cannot attribute "
                    "this application to a specific job board or channel. It will be "
                    "grouped under Other."
                ),
                analytics_impact=(
                    "Source ROI cannot attribute this application to a specific channel; "
                    "it is grouped under Other."
                ),
                severity=_SAVE_QUALITY_SEVERITY_CRITICAL,
            ),
        )

    if _strip_or_empty(application.cv_version) == "":
        warnings.append(
            SaveQualityWarning(
                field_name="cv_version",
                message=(
                    "CV version is missing - CV Version Performance analytics cannot "
                    "track which CV was used for this application."
                ),
                analytics_impact="CV Version Performance cannot group/track this application.",
                severity=_SAVE_QUALITY_SEVERITY_CRITICAL,
            ),
        )

    if _strip_or_empty(application.location) == "":
        warnings.append(
            SaveQualityWarning(
                field_name="location",
                message="Location is not saved.",
                analytics_impact="Smart Review location component scores 0.",
                severity=_SAVE_QUALITY_SEVERITY_IMPORTANT,
            ),
        )

    if len(_strip_or_empty(application.required_skills)) < _MIN_REQUIRED_SKILLS_CHARS:
        warnings.append(
            SaveQualityWarning(
                field_name="required_skills",
                message="Required skills are too short for reliable matching.",
                analytics_impact=(
                    "Smart Review skills matching and Rejection Pattern analysis are unreliable."
                ),
                severity=_SAVE_QUALITY_SEVERITY_IMPORTANT,
            ),
        )

    if len(_strip_or_empty(application.job_description)) < _MIN_JOB_DESCRIPTION_CHARS:
        warnings.append(
            SaveQualityWarning(
                field_name="job_description",
                message="Job description is too short for deal-breaker detection.",
                analytics_impact="Smart Review deal-breaker detection cannot run.",
                severity=_SAVE_QUALITY_SEVERITY_IMPORTANT,
            ),
        )

    return warnings
