from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.applications.models import JobApplication

from .draft_documents import build_application_document_drafts, save_application_document_drafts
from .services import build_skill_intelligence_context, build_smart_review, build_smart_review_rows


@login_required
def smart_review(request):
    return render(
        request,
        "job_intelligence/smart_review.html",
        {"rows": build_smart_review_rows(request.user)},
    )


@login_required
def skill_intelligence(request):
    return render(
        request,
        "job_intelligence/skill_intelligence.html",
        {"skill_intelligence": build_skill_intelligence_context(request.user)},
    )


@login_required
def application_smart_review(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    review = build_smart_review(application)
    document_drafts = None
    drafts_saved = False
    if request.method == "POST":
        action = request.POST.get("action")
        if action in {"generate_drafts", "save_drafts"}:
            document_drafts = build_application_document_drafts(application, review)
        if action == "save_drafts" and document_drafts is not None:
            save_application_document_drafts(application, document_drafts)
            drafts_saved = True
            messages.success(
                request,
                "Draft CV and cover letter saved to the Application Document Pack.",
            )
    return render(
        request,
        "job_intelligence/application_smart_review.html",
        {
            "application": application,
            "review": review,
            "document_drafts": document_drafts,
            "drafts_saved": drafts_saved,
            "show_save_drafts_action": True,
        },
    )
