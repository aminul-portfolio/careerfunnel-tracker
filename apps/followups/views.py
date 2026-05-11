from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.applications.models import JobApplication

from .services import get_due_followups, get_followup_applications, mark_followup_sent


@login_required
def followup_list(request):
    applications = get_followup_applications(request.user)
    due_followups = get_due_followups(request.user)
    return render(
        request,
        "followups/followup_list.html",
        {"applications": applications, "due_followups": due_followups, "due_count": due_followups.count()},
    )


@login_required
def mark_sent(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    if request.method == "POST":
        mark_followup_sent(application)
        messages.success(request, "Follow-up marked as sent.")
    return redirect("followups:followup_list")
