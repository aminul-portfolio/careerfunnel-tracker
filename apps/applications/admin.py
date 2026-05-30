from django.contrib import admin

from .models import ApplicationDocument, JobApplication


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = [
        "company_name",
        "job_title",
        "user",
        "status",
        "role_fit",
        "date_applied",
        "response_date",
        "work_type",
        "source",
    ]
    list_filter = ["status", "role_fit", "work_type", "source", "date_applied"]
    search_fields = [
        "company_name",
        "job_title",
        "location",
        "notes",
        "contact_name",
        "contact_email",
    ]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(ApplicationDocument)
class ApplicationDocumentAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "document_type",
        "status",
        "source",
        "application",
        "updated_at",
    ]
    list_filter = ["document_type", "status", "source"]
    search_fields = [
        "name",
        "application__company_name",
        "application__job_title",
        "content",
        "tailoring_notes",
    ]
    readonly_fields = ["created_at", "updated_at"]
