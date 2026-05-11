from django.contrib import admin

from .models import DailyLog


@admin.register(DailyLog)
class DailyLogAdmin(admin.ModelAdmin):
    list_display = ["log_date", "user", "target_applications", "actual_applications", "variance", "responses_received", "calls_received", "hours_spent", "energy_level"]
    list_filter = ["log_date", "energy_level"]
    search_fields = ["user__username", "notes"]
    readonly_fields = ["created_at", "updated_at"]
