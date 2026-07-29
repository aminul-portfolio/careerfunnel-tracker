from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import SkillEntry


@admin.register(SkillEntry)
class SkillEntryAdmin(admin.ModelAdmin):
    list_display = [
        "skill_name",
        "user",
        "category",
        "evidence_level",
        "visibility",
        "sprint_reference",
        "date_added",
        "last_updated",
    ]
    list_filter = ["user", "category", "evidence_level", "visibility"]
    list_select_related = ("user",)
    search_fields = ["skill_name", "sprint_reference"]

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and "user" not in readonly_fields:
            readonly_fields.append("user")
        return readonly_fields

    def get_fields(self, request, obj=None):
        fields = list(super().get_fields(request, obj))
        if "user" not in fields:
            fields.insert(0, "user")
        return fields

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "user" and formfield is not None:
            formfield.required = True
            User = get_user_model()
            formfield.queryset = User.objects.order_by("username")
        return formfield

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            if not change or obj.user_id is None:
                obj.user = request.user
            else:
                # Preserve the existing owner for ordinary staff edits.
                original = (
                    SkillEntry.objects.filter(pk=obj.pk).only("user_id").first()
                )
                if original is not None:
                    obj.user_id = original.user_id
                else:
                    obj.user = request.user
        super().save_model(request, obj, form, change)
