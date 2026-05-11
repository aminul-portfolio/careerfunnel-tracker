from django.urls import path

from . import views

app_name = "exports"

urlpatterns = [
    path("", views.export_center, name="export_center"),
    path("applications/", views.export_applications, name="export_applications"),
    path("daily-logs/", views.export_daily_logs, name="export_daily_logs"),
    path("weekly-reviews/", views.export_weekly_reviews, name="export_weekly_reviews"),
    path("interviews/", views.export_interviews, name="export_interviews"),
    path("notes/", views.export_notes, name="export_notes"),
    path("full-tracker/", views.export_full_tracker, name="export_full_tracker"),
]
