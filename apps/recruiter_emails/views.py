import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.applications.models import JobApplication

from .choices import ReplyStatus
from .forms import RecruiterEmailImportForm
from .models import RecruiterEmail


def _get_user_recruiter_email(request, pk):
    return get_object_or_404(
        RecruiterEmail,
        pk=pk,
        application__user=request.user,
    )


def _parse_matched_signals(recruiter_email: RecruiterEmail) -> list[str]:
    if not recruiter_email.matched_signals:
        return []
    try:
        parsed = json.loads(recruiter_email.matched_signals)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


@login_required
def import_recruiter_email(request, application_id):
    application = get_object_or_404(
        JobApplication,
        pk=application_id,
        user=request.user,
    )
    if request.method == "POST":
        form = RecruiterEmailImportForm(
            request.POST,
            application=application,
        )
        if form.is_valid():
            recruiter_email = form.save()
            messages.success(request, "Recruiter email imported successfully.")
            return redirect("recruiter_emails:detail", pk=recruiter_email.pk)
    else:
        form = RecruiterEmailImportForm(application=application)

    return render(
        request,
        "recruiter_emails/import_form.html",
        {
            "form": form,
            "application": application,
        },
    )


@login_required
def recruiter_email_detail(request, pk):
    recruiter_email = _get_user_recruiter_email(request, pk)
    return render(
        request,
        "recruiter_emails/detail.html",
        {
            "recruiter_email": recruiter_email,
            "matched_signals_list": _parse_matched_signals(recruiter_email),
        },
    )


@login_required
@require_POST
def mark_recruiter_email_sent(request, pk):
    recruiter_email = _get_user_recruiter_email(request, pk)
    recruiter_email.reply_status = ReplyStatus.SENT_MANUALLY
    recruiter_email.save(update_fields=["reply_status", "updated_at"])
    messages.success(request, "Reply marked as sent manually.")
    return redirect("recruiter_emails:detail", pk=recruiter_email.pk)
