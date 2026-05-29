from django.urls import path

from . import views

app_name = "skills"

urlpatterns = [
    path(
        "ai-capability-framework/",
        views.ai_capability_framework,
        name="ai_capability_framework",
    ),
    path(
        "ai-readiness-report/",
        views.ai_readiness_report,
        name="ai_readiness_report",
    ),
    path(
        "job-ai-capability-match/",
        views.job_ai_capability_match_report,
        name="job_ai_capability_match_report",
    ),
]
