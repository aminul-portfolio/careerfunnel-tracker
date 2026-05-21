from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from .choices import EmailType, ImportSource, ReplyStatus
from .models import RecruiterEmail

REJECTION_SIGNALS = [
    "unfortunately",
    "not be progressing",
    "not be moving forward",
    "unsuccessful",
    "after careful consideration",
    "we have decided not to proceed",
    "will not be taking your application further",
]

ROLE_CLOSED_SIGNALS = [
    "role has been closed",
    "position has been filled",
    "vacancy has been filled",
    "role is on hold",
    "recruitment is on hold",
    "hiring has been paused",
]

OFFER_SIGNALS = [
    "offer",
    "next steps",
    "we would like to offer",
    "pleased to offer",
    "conditional offer",
]

TASK_TEST_SIGNALS = [
    "technical test",
    "assessment",
    "take-home task",
    "task to complete",
    "coding test",
    "excel test",
    "case study",
]

RESCHEDULE_SIGNALS = [
    "reschedule",
    "rearrange",
    "cancelled",
    "cancellation",
    "postpone",
    "move our call",
]

SCREENING_SIGNALS = [
    "screening call",
    "initial call",
    "phone screen",
    "recruiter screen",
    "quick call",
    "introductory call",
]

INTERVIEW_SIGNALS = [
    "interview",
    "invite you to interview",
    "interview availability",
    "interview slot",
    "meet the hiring manager",
]

AVAILABILITY_SIGNALS = [
    "availability",
    "available for a call",
    "when are you free",
    "suitable time",
    "time slots",
]

SALARY_SIGNALS = [
    "salary expectation",
    "salary expectations",
    "day rate",
    "compensation",
    "expected salary",
    "desired salary",
]

RIGHT_TO_WORK_SIGNALS = [
    "right to work",
    "work authorisation",
    "work authorization",
    "visa status",
    "require sponsorship",
    "sponsorship",
]

LOCATION_WORK_MODE_SIGNALS = [
    "location",
    "hybrid",
    "remote",
    "onsite",
    "on-site",
    "office days",
    "commute",
]

DOCUMENT_REQUEST_SIGNALS = [
    "proof of address",
    "id document",
    "identification",
    "passport",
    "share documents",
    "references",
]

CV_REQUEST_SIGNALS = [
    "send your cv",
    "updated cv",
    "latest cv",
    "portfolio",
    "github",
    "work samples",
]

NEW_OPPORTUNITY_SIGNALS = [
    "new opportunity",
    "role that may suit",
    "opportunity with",
    "hiring for",
    "vacancy for",
]

INTEREST_SIGNALS = [
    "impressed with your profile",
    "interested in your profile",
    "would like to discuss",
    "your background looks relevant",
    "came across your profile",
]

ACKNOWLEDGEMENT_SIGNALS = [
    "thank you for applying",
    "application received",
    "received your application",
    "we have received",
    "thanks for your application",
]

EMAIL_TYPE_PRIORITY: list[tuple[str, list[str]]] = [
    (EmailType.REJECTION, REJECTION_SIGNALS),
    (EmailType.ROLE_CLOSED_OR_ON_HOLD, ROLE_CLOSED_SIGNALS),
    (EmailType.OFFER_OR_NEXT_STEPS, OFFER_SIGNALS),
    (EmailType.TASK_OR_TEST, TASK_TEST_SIGNALS),
    (EmailType.RESCHEDULE_OR_CANCELLATION, RESCHEDULE_SIGNALS),
    (EmailType.SCREENING_INVITE, SCREENING_SIGNALS),
    (EmailType.INTERVIEW_INVITE, INTERVIEW_SIGNALS),
    (EmailType.AVAILABILITY_REQUEST, AVAILABILITY_SIGNALS),
    (EmailType.SALARY_QUESTION, SALARY_SIGNALS),
    (EmailType.RIGHT_TO_WORK_QUESTION, RIGHT_TO_WORK_SIGNALS),
    (EmailType.LOCATION_WORK_MODE_QUESTION, LOCATION_WORK_MODE_SIGNALS),
    (EmailType.DOCUMENT_REQUEST, DOCUMENT_REQUEST_SIGNALS),
    (EmailType.CV_REQUEST, CV_REQUEST_SIGNALS),
    (EmailType.NEW_OPPORTUNITY, NEW_OPPORTUNITY_SIGNALS),
    (EmailType.INTEREST, INTEREST_SIGNALS),
    (EmailType.ACKNOWLEDGEMENT, ACKNOWLEDGEMENT_SIGNALS),
]


@dataclass(frozen=True)
class RecruiterEmailClassification:
    email_type: str
    matched_signals: list[str]
    classification_rationale: str
    requires_reply: bool
    suggested_application_status: str


def _normalise_email_text(subject: str = "", body: str = "") -> str:
    return f"{subject} {body}".strip().lower()


def _find_matched_signals(text: str, signals: list[str]) -> list[str]:
    return [signal for signal in signals if signal in text]


def classify_recruiter_email(
    subject: str = "",
    body: str = "",
) -> RecruiterEmailClassification:
    text = _normalise_email_text(subject, body)
    if not text:
        return RecruiterEmailClassification(
            email_type=EmailType.UNKNOWN,
            matched_signals=[],
            classification_rationale=(
                "No recruiter email content was available to classify."
            ),
            requires_reply=requires_reply_for_email_type(EmailType.UNKNOWN),
            suggested_application_status=suggest_status_update(EmailType.UNKNOWN),
        )

    for email_type, signals in EMAIL_TYPE_PRIORITY:
        matched = _find_matched_signals(text, signals)
        if matched:
            return RecruiterEmailClassification(
                email_type=email_type,
                matched_signals=matched,
                classification_rationale=(
                    f"Matched {email_type.replace('_', ' ')} signals in recruiter "
                    "email content."
                ),
                requires_reply=requires_reply_for_email_type(email_type),
                suggested_application_status=suggest_status_update(email_type),
            )

    return RecruiterEmailClassification(
        email_type=EmailType.OTHER,
        matched_signals=[],
        classification_rationale=(
            "No specific recruiter email type signals were matched."
        ),
        requires_reply=requires_reply_for_email_type(EmailType.OTHER),
        suggested_application_status=suggest_status_update(EmailType.OTHER),
    )


def requires_reply_for_email_type(email_type: str) -> bool:
    return email_type not in {
        EmailType.ACKNOWLEDGEMENT,
        EmailType.REJECTION,
        EmailType.ROLE_CLOSED_OR_ON_HOLD,
    }


def suggest_status_update(email_type: str) -> str:
    status_map = {
        EmailType.ACKNOWLEDGEMENT: "applied",
        EmailType.INTEREST: "recruiter_interest",
        EmailType.NEW_OPPORTUNITY: "recruiter_interest",
        EmailType.AVAILABILITY_REQUEST: "follow_up_due",
        EmailType.SCREENING_INVITE: "screening",
        EmailType.INTERVIEW_INVITE: "interview",
        EmailType.RESCHEDULE_OR_CANCELLATION: "follow_up_due",
        EmailType.TASK_OR_TEST: "assessment",
        EmailType.CV_REQUEST: "follow_up_due",
        EmailType.DOCUMENT_REQUEST: "follow_up_due",
        EmailType.SALARY_QUESTION: "follow_up_due",
        EmailType.RIGHT_TO_WORK_QUESTION: "follow_up_due",
        EmailType.LOCATION_WORK_MODE_QUESTION: "follow_up_due",
        EmailType.REJECTION: "rejected",
        EmailType.ROLE_CLOSED_OR_ON_HOLD: "closed_or_on_hold",
        EmailType.OFFER_OR_NEXT_STEPS: "offer_or_next_steps",
    }
    return status_map.get(email_type, "")


def suggest_action_due_at(email_type: str, date_received):
    if date_received is None:
        return None

    hours_map = {
        EmailType.INTERVIEW_INVITE: 24,
        EmailType.SCREENING_INVITE: 24,
        EmailType.AVAILABILITY_REQUEST: 48,
        EmailType.INTEREST: 72,
        EmailType.NEW_OPPORTUNITY: 72,
        EmailType.TASK_OR_TEST: 48,
        EmailType.CV_REQUEST: 48,
        EmailType.DOCUMENT_REQUEST: 48,
        EmailType.SALARY_QUESTION: 48,
        EmailType.RIGHT_TO_WORK_QUESTION: 48,
        EmailType.LOCATION_WORK_MODE_QUESTION: 48,
        EmailType.RESCHEDULE_OR_CANCELLATION: 24,
        EmailType.OFFER_OR_NEXT_STEPS: 24,
    }
    hours = hours_map.get(email_type)
    if hours is None:
        return None

    received = date_received
    if timezone.is_naive(received):
        received = timezone.make_aware(received, timezone.get_current_timezone())
    return received + timedelta(hours=hours)


def serialise_matched_signals(signals: list[str]) -> str:
    return json.dumps(signals)


def _company_label(application) -> str:
    if application and getattr(application, "company_name", None):
        return application.company_name
    return "[Company name]"


def _role_label(application) -> str:
    if application and getattr(application, "job_title", None):
        return application.job_title
    return "[Role title]"


def _salary_wording(application) -> str:
    if application and getattr(application, "salary_range", "").strip():
        return (
            f"My salary expectation for this role is {application.salary_range.strip()}, "
            "subject to the full package and scope."
        )
    return (
        "My salary expectation is negotiable depending on the role scope and overall package."
    )


def generate_reply_draft(email_type: str, application=None) -> str:
    company = _company_label(application)
    role = _role_label(application)

    if email_type in {
        EmailType.ACKNOWLEDGEMENT,
        EmailType.REJECTION,
        EmailType.ROLE_CLOSED_OR_ON_HOLD,
    }:
        return ""

    if email_type == EmailType.INTEREST:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} opportunity at {company}. "
            "I would welcome a brief discussion to learn more about the role and next steps.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.NEW_OPPORTUNITY:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for sharing the new opportunity at {company}. "
            f"I would be interested in learning more about the {role} role and whether it "
            "would be a good fit.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.AVAILABILITY_REQUEST:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} role at {company}. "
            "I am available at the following times: [insert your availability slots].\n\n"
            "Please let me know which option works best.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.SCREENING_INVITE:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for inviting me to a screening call for the {role} role at {company}. "
            "I am available at the following times: [insert your availability slots].\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.INTERVIEW_INVITE:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for the interview invitation for the {role} role at {company}. "
            "I am available at the following times: [insert your availability slots].\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.RESCHEDULE_OR_CANCELLATION:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your update regarding the {role} opportunity at {company}. "
            "I am available at the following times: [insert your availability slots].\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.TASK_OR_TEST:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} role at {company}. "
            "I confirm I can complete the requested assessment and will review the "
            "instructions carefully before submitting.\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.CV_REQUEST:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} role at {company}. "
            "Please find my CV attached: [attach CV file]. "
            "Portfolio/work samples: [add link if relevant].\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.DOCUMENT_REQUEST:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} role at {company}. "
            "I will share the requested documents shortly: [list documents to attach].\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.SALARY_QUESTION:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} role at {company}. "
            f"{_salary_wording(application)}\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.RIGHT_TO_WORK_QUESTION:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} role at {company}. "
            "[Confirm your right-to-work status before sending.]\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.LOCATION_WORK_MODE_QUESTION:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your message regarding the {role} role at {company}. "
            "My preferred work arrangement is: [insert hybrid/remote/onsite preference].\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    if email_type == EmailType.OFFER_OR_NEXT_STEPS:
        return (
            f"Dear Hiring Team,\n\n"
            f"Thank you for your update regarding the {role} opportunity at {company}. "
            "Could you please share the written offer details and confirm the next steps?\n\n"
            "Kind regards,\n"
            "Aminul Islam"
        )

    return (
        f"Dear Hiring Team,\n\n"
        f"Thank you for your message regarding the {role} opportunity at {company}. "
        "Please let me know the next steps.\n\n"
        "Kind regards,\n"
        "Aminul Islam"
    )


def _resolve_reply_status(*, requires_reply: bool, reply_draft: str) -> str:
    if not requires_reply:
        return ReplyStatus.NOT_REQUIRED
    if reply_draft.strip():
        return ReplyStatus.DRAFTED
    return ReplyStatus.NEEDS_REVIEW


def create_recruiter_email_from_form_data(*, application, cleaned_data) -> RecruiterEmail:
    if application is None:
        raise ValueError("application is required for Sprint 28A recruiter email import.")

    subject = cleaned_data.get("subject", "")
    body = cleaned_data["body"]
    date_received = cleaned_data["date_received"]

    classification = classify_recruiter_email(subject=subject, body=body)
    reply_draft = generate_reply_draft(classification.email_type, application)

    recruiter_email = RecruiterEmail.objects.create(
        application=application,
        subject=subject,
        sender_name=cleaned_data.get("sender_name", ""),
        sender_email=cleaned_data.get("sender_email", ""),
        body=body,
        date_received=date_received,
        email_type=classification.email_type,
        matched_signals=serialise_matched_signals(classification.matched_signals),
        classification_rationale=classification.classification_rationale,
        reply_draft=reply_draft,
        reply_status=_resolve_reply_status(
            requires_reply=classification.requires_reply,
            reply_draft=reply_draft,
        ),
        requires_reply=classification.requires_reply,
        action_due_at=suggest_action_due_at(classification.email_type, date_received),
        suggested_application_status=classification.suggested_application_status,
        import_source=ImportSource.MANUAL,
        notes=cleaned_data.get("notes", ""),
    )
    return recruiter_email
