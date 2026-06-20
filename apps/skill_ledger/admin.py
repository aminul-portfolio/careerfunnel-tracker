from django.contrib import admin

from .models import SkillEntry


@admin.register(SkillEntry)
class SkillEntryAdmin(admin.ModelAdmin):
    list_display = [
        "skill_name",
        "category",
        "evidence_level",
        "visibility",
        "sprint_reference",
        "date_added",
        "last_updated",
    ]
    list_filter = ["category", "evidence_level", "visibility"]
    search_fields = ["skill_name", "sprint_reference", "notes"]
