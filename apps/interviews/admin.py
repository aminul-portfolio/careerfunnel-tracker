from django.contrib import admin

from .models import InterviewPrep


@admin.register(InterviewPrep)
class InterviewPrepAdmin(admin.ModelAdmin):
    list_display = ["application", "user", "interview_date", "stage", "outcome", "readiness_score"]
    list_filter = ["stage", "outcome", "interview_date"]
    search_fields = [
        "application__company_name",
        "application__job_title",
        "expected_topics",
        "reflection",
    ]
