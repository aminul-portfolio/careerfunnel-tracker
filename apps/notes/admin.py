from django.contrib import admin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "note_type", "decision_date", "is_important", "created_at"]
    list_filter = ["note_type", "is_important", "decision_date", "created_at"]
    search_fields = ["title", "content", "tags", "user__username"]
    readonly_fields = ["created_at", "updated_at"]
