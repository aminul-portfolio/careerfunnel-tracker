from django import forms

from .models import Note


class NoteForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = ["note_type", "title", "content", "tags", "decision_date", "is_important"]
        widgets = {
            "note_type": forms.Select(attrs={"class": "form-control"}),
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Changed CV headline",
                }
            ),
            "content": forms.Textarea(attrs={"class": "form-control", "rows": 7}),
            "tags": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "CV, LinkedIn, screening",
                }
            ),
            "decision_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "is_important": forms.CheckboxInput(attrs={"class": "checkbox-input"}),
        }
