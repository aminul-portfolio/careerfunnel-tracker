from django.contrib import admin

from .models import ApplicationSkillGap


@admin.register(ApplicationSkillGap)
class ApplicationSkillGapAdmin(admin.ModelAdmin):
    list_display = [
        "skill_name",
        "application",
        "stage",
        "current_tier",
        "priority",
        "priority_score",
        "failure_count",
        "resolved",
        "updated_at",
    ]
    list_filter = [
        "stage",
        "priority",
        "current_tier",
        "resolved",
        "identified_by",
        "long_term_goal",
    ]
    search_fields = [
        "skill_name",
        "jd_requirement",
        "suggested_action",
        "application__company_name",
        "application__job_title",
        "application__user__username",
    ]
    readonly_fields = ["created_at", "updated_at"]
