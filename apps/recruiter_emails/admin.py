from django.contrib import admin

from .models import RecruiterEmail


@admin.register(RecruiterEmail)
class RecruiterEmailAdmin(admin.ModelAdmin):
    list_display = [
        "subject",
        "application",
        "email_type",
        "reply_status",
        "requires_reply",
        "date_received",
        "action_due_at",
        "import_source",
    ]
    list_filter = [
        "email_type",
        "reply_status",
        "requires_reply",
        "import_source",
        "date_received",
        "action_due_at",
    ]
    search_fields = [
        "subject",
        "sender_name",
        "sender_email",
        "body",
        "application__company_name",
        "application__job_title",
    ]
    readonly_fields = ["created_at", "updated_at"]
