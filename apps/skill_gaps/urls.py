from django.urls import path

from . import views

app_name = "skill_gaps"

urlpatterns = [
    path("ai-career-coach/", views.ai_career_coach_view, name="ai_career_coach"),
    path("", views.dashboard, name="dashboard"),
]
