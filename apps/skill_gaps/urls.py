from django.urls import path

from . import views

app_name = "skill_gaps"

urlpatterns = [
    path("ai-career-coach/", views.ai_career_coach_view, name="ai_career_coach"),
    path("jd-enrichment/", views.jd_requirement_enrichment_view, name="jd_requirement_enrichment"),
    path("", views.dashboard, name="dashboard"),
]
