from django import forms

from .models import SkillEntry


class SkillEntryForm(forms.ModelForm):
    class Meta:
        model = SkillEntry
        fields = [
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
        ]
        help_texts = {
            "evidence_level": (
                "VERIFIED means portfolio evidence exists in a closed sprint, passing tests, "
                "or prior work experience - not external certification."
            ),
        }
