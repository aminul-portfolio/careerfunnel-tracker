from django.contrib import admin

from .models import WeeklyReview


@admin.register(WeeklyReview)
class WeeklyReviewAdmin(admin.ModelAdmin):
    list_display = [
        "week_ending",
        "user",
        "target_applications",
        "actual_applications",
        "application_variance",
        "responses_received",
        "screening_calls",
        "interviews",
        "offers",
        "diagnosis",
        "mood",
    ]
    list_filter = ["diagnosis", "mood", "week_ending"]
    search_fields = [
        "user__username",
        "what_worked",
        "what_blocked",
        "lessons_learned",
        "change_next_week",
    ]
    readonly_fields = ["created_at", "updated_at"]
