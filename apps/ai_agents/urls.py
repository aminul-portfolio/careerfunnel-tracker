from django.urls import path

from . import views

app_name = "ai_agents"

urlpatterns = [
    path("", views.agent_dashboard, name="agent_dashboard"),
    path("job-posting-analyzer/", views.job_posting_analyzer, name="job_posting_analyzer"),
    path("next-best-actions/", views.next_best_actions, name="next_best_actions"),
    path("follow-up-writer/", views.followup_writer, name="followup_writer"),
    path("interview-prep-generator/", views.interview_prep_generator, name="interview_prep_generator"),
    path("weekly-coach/", views.weekly_coach, name="weekly_coach"),
    path("cv-gap-analyzer/", views.cv_gap_analyzer, name="cv_gap_analyzer"),
    path("cover-letter-quality-checker/", views.cover_letter_quality_checker, name="cover_letter_quality_checker"),
    path("rejection-pattern-analyzer/", views.rejection_pattern_analyzer, name="rejection_pattern_analyzer"),
    path("cv-ab-testing/", views.cv_ab_testing, name="cv_ab_testing"),
    path("smart-notifications/", views.smart_notifications, name="smart_notifications"),
    path("application/<int:pk>/", views.application_agent_pack, name="application_agent_pack"),
]
