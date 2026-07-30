from django.urls import path

from . import deterministic_gap_views, views

app_name = "skill_gaps"

urlpatterns = [
    path("ai-career-coach/", views.ai_career_coach_view, name="ai_career_coach"),
    path("jd-enrichment/", views.jd_requirement_enrichment_view, name="jd_requirement_enrichment"),
    path(
        "jd-gap-analysis/",
        deterministic_gap_views.jd_gap_analysis_view,
        name="jd_gap_analysis",
    ),
    path("", views.dashboard, name="dashboard"),
]
