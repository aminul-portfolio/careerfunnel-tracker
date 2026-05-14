from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.applications.models import JobApplication

from .services import build_smart_review, build_smart_review_rows


@login_required
def smart_review(request):
    return render(
        request,
        "job_intelligence/smart_review.html",
        {"rows": build_smart_review_rows(request.user)},
    )


@login_required
def application_smart_review(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    return render(
        request,
        "job_intelligence/application_smart_review.html",
        {"application": application, "review": build_smart_review(application)},
    )
