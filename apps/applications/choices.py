from django.db import models


class ApplicationStatus(models.TextChoices):
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


class ApplicationSource(models.TextChoices):
    LINKEDIN = "linkedin", "LinkedIn"
    INDEED = "indeed", "Indeed"
    GLASSDOOR = "glassdoor", "Glassdoor"
    WELCOME_TO_THE_JUNGLE = "welcome_to_the_jungle", "Welcome to the Jungle"
    COMPANY_WEBSITE = "company_website", "Company website"
    RECRUITER = "recruiter", "Recruiter"
    REFERRAL = "referral", "Referral"
    OTHER = "other", "Other"
