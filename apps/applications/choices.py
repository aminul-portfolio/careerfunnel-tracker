from django.db import models


class ApplicationStatus(models.TextChoices):
    SAVED_FOR_LATER = "saved_for_later", "Saved for later"
    SUBMITTED = "submitted", "Submitted"
    AUTO_REJECTED = "auto_rejected", "Auto-rejected"
    NO_RESPONSE = "no_response", "No response"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    SCREENING_CALL = "screening_call", "Screening call"
    TECHNICAL_SCREEN = "technical_screen", "Technical screen"
    INTERVIEW = "interview", "Interview"
    OFFER = "offer", "Offer"
    REJECTED = "rejected", "Rejected"
    WITHDREW = "withdrew", "Withdrew"


class PipelineStage(models.TextChoices):
    SAVED_FOR_LATER = "saved_for_later", "Saved for later"
    JOB_FOUND = "job_found", "Job found"
    FIT_CHECKED = "fit_checked", "Fit checked"
    CV_SELECTED = "cv_selected", "CV selected"
    COVER_LETTER_DRAFTED = "cover_letter_drafted", "Cover letter drafted"
    SUBMITTED = "submitted", "Application submitted"
    FOLLOW_UP_DUE = "follow_up_due", "Follow-up due"
    RECRUITER_RESPONDED = "recruiter_responded", "Recruiter responded"
    SCREENING_CALL = "screening_call", "Screening call"
    TECHNICAL_TASK = "technical_task", "Technical / task stage"
    INTERVIEW = "interview", "Interview"
    FINAL_INTERVIEW = "final_interview", "Final interview"
    CLOSED = "closed", "Closed"


class FollowUpStatus(models.TextChoices):
    NOT_SET = "not_set", "Not set"
    NOT_DUE = "not_due", "Not due"
    DUE = "due", "Due"
    SENT = "sent", "Sent"
    RESPONDED = "responded", "Responded"
    NOT_NEEDED = "not_needed", "Not needed"


class WorkType(models.TextChoices):
    REMOTE = "remote", "Remote"
    HYBRID = "hybrid", "Hybrid"
    ONSITE = "onsite", "On-site"
    FLEXIBLE = "flexible", "Flexible"
    UNKNOWN = "unknown", "Unknown"


class RoleFit(models.TextChoices):
    STRONG = "strong", "Strong fit"
    MEDIUM = "medium", "Medium fit"
    WEAK = "weak", "Weak fit"
    UNKNOWN = "unknown", "Unknown"


class DocumentType(models.TextChoices):
    CV = "cv", "CV"
    COVER_LETTER = "cover_letter", "Cover letter"


class DocumentStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    REVIEWED = "reviewed", "Reviewed"
    READY_FOR_MANUAL_SUBMISSION = (
        "ready_for_manual_submission",
        "Ready for manual submission",
    )
    SUBMITTED = "submitted", "Submitted"
    ARCHIVED = "archived", "Archived"


class DocumentSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    JOB_ANALYZER = "job_analyzer", "Job analyzer"
    MASTER_CV_BASELINE = "master_cv_baseline", "Master CV baseline"
    USER_UPLOAD = "user_upload", "User uploaded"


UPLOADED_CV_DOCUMENT_NAME = "Uploaded Final CV"
UPLOADED_COVER_LETTER_DOCUMENT_NAME = "Uploaded Final Cover Letter"

ALLOWED_UPLOAD_EXTENSIONS = frozenset({"pdf", "docx", "txt"})
MAX_UPLOAD_FILE_SIZE_BYTES = 5 * 1024 * 1024


DEFAULT_CV_BASELINE_NAME = "Aminul_Islam_Data_Analyst_CV"

LEGACY_CV_VERSION_LABELS = frozenset(
    {
        "Finance_DA_CV_v1",
        "BI_Reporting_CV_v1",
        "DA_CV_v1",
        "DA_CV_v2",
    }
)

LEGACY_COVER_LETTER_VERSION_LABELS = frozenset(
    {
        "Tailored_CL_v1",
        "Tailored_CL_v2",
    }
)

DEFAULT_COVER_LETTER_DRAFT_LABEL = "Aminul_Islam_Cover_Letter_Draft"

GENERIC_COVER_LETTER_DRAFT_LABEL = "Draft cover letter"


class ApplicationSource(models.TextChoices):
    REED = "reed", "Reed.co.uk"
    LINKEDIN = "linkedin", "LinkedIn"
    INDEED = "indeed", "Indeed"
    GLASSDOOR = "glassdoor", "Glassdoor"
    WELCOME_TO_THE_JUNGLE = "welcome_to_the_jungle", "Welcome to the Jungle"
    COMPANY_WEBSITE = "company_website", "Company Website"
    RECRUITER = "recruiter", "Recruiter"
    REFERRAL = "referral", "Referral"
    BOOKMARKLET = "bookmarklet", "Bookmarklet"
    OTHER = "other", "Other"
