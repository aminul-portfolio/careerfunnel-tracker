from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Count

from .choices import ApplicationSource, ApplicationStatus, FollowUpStatus
from .selectors import get_user_applications


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


def _has_cv_version(application) -> bool:
    return _strip_or_empty(application.cv_version) != ""


def _has_cover_letter_version(application) -> bool:
    return _strip_or_empty(application.cover_letter_version) != ""


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
                    "Source is set to the generic 'Other' — Source ROI cannot attribute "
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
                    "CV version is missing — CV Version Performance analytics cannot "
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
