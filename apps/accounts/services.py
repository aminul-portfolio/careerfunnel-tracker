from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth.models import User
from django.utils import timezone

from apps.applications.models import JobApplication

WORKSPACE_ROLE_LABEL = "Manual career intelligence workspace member"
ACCOUNT_STATUS_LABEL = "Authenticated portfolio workspace"
CLAIM_SAFE_WORKSPACE_NOTE = (
    "This workspace is manual, evidence-led, and advisory. "
    "CareerFunnel Tracker does not auto-apply, scrape job boards, "
    "or submit applications on your behalf."
)
LOCKED_CV_REFERENCE = "Aminul_Islam_Data_Analyst_CV"
PREFERRED_ROLE_FOCUS = "Data Analyst"


@dataclass(frozen=True)
class WorkspaceSummaryItem:
    label: str
    value: str


@dataclass(frozen=True)
class AccountProfileViewModel:
    display_name: str
    username: str
    email: str
    role_label: str
    account_status: str
    last_login_display: str
    date_joined_display: str
    workspace_summary: tuple[WorkspaceSummaryItem, ...]
    claim_safe_note: str


@dataclass(frozen=True)
class AccountSettingsViewModel:
    last_login_display: str
    locked_cv_reference: str
    preferred_role_focus: str
    claim_safe_note: str


def account_display_name(user: User) -> str:
    full_name = (user.get_full_name() or "").strip()
    return full_name or user.username


def account_initials(user: User) -> str:
    display = account_display_name(user)
    parts = [part for part in display.split() if part]
    if len(parts) >= 2:
        return f"{parts[0][0]}{parts[-1][0]}".upper()
    if display:
        return display[:2].upper()
    return "CF"


def _format_datetime(value) -> str:
    if value is None:
        return "Not recorded yet"
    localized = timezone.localtime(value) if timezone.is_aware(value) else value
    return localized.strftime("%Y-%m-%d %H:%M")


def build_account_profile_context(user: User) -> AccountProfileViewModel:
    application_count = JobApplication.objects.filter(user=user).count()
    return AccountProfileViewModel(
        display_name=account_display_name(user),
        username=user.username,
        email=user.email or "No email saved",
        role_label=WORKSPACE_ROLE_LABEL,
        account_status=ACCOUNT_STATUS_LABEL,
        last_login_display=_format_datetime(user.last_login),
        date_joined_display=_format_datetime(user.date_joined),
        workspace_summary=(
            WorkspaceSummaryItem("Saved applications", str(application_count)),
            WorkspaceSummaryItem("Workspace type", "Local portfolio workspace"),
            WorkspaceSummaryItem("Workflow mode", "Manual review only"),
        ),
        claim_safe_note=CLAIM_SAFE_WORKSPACE_NOTE,
    )


def build_account_settings_context(user: User) -> AccountSettingsViewModel:
    return AccountSettingsViewModel(
        last_login_display=_format_datetime(user.last_login),
        locked_cv_reference=LOCKED_CV_REFERENCE,
        preferred_role_focus=PREFERRED_ROLE_FOCUS,
        claim_safe_note=CLAIM_SAFE_WORKSPACE_NOTE,
    )
