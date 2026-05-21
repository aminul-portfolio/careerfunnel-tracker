from django import forms

from .models import RecruiterEmail
from .services import create_recruiter_email_from_form_data


class RecruiterEmailImportForm(forms.ModelForm):
    class Meta:
        model = RecruiterEmail
        fields = [
            "subject",
            "sender_name",
            "sender_email",
            "body",
            "date_received",
            "notes",
        ]
        labels = {
            "subject": "Email subject",
            "sender_name": "Sender name",
            "sender_email": "Sender email",
            "body": "Email body",
            "date_received": "Date received",
            "notes": "Internal notes",
        }
        widgets = {
            "subject": forms.TextInput(attrs={"class": "form-control"}),
            "sender_name": forms.TextInput(attrs={"class": "form-control"}),
            "sender_email": forms.EmailInput(attrs={"class": "form-control"}),
            "body": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 10,
                    "placeholder": "Paste the recruiter email content here.",
                }
            ),
            "date_received": forms.DateTimeInput(
                attrs={"class": "form-control", "type": "datetime-local"},
                format="%Y-%m-%dT%H:%M",
            ),
            "notes": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Optional notes for your own tracking.",
                }
            ),
        }

    def __init__(self, *args, application=None, **kwargs):
        self.application = application
        super().__init__(*args, **kwargs)
        self.fields["body"].required = True
        self.fields["date_received"].required = True

    def clean(self):
        cleaned_data = super().clean()
        if not self.application:
            raise forms.ValidationError(
                "An application is required to import a recruiter email."
            )
        if not cleaned_data.get("body", "").strip():
            self.add_error("body", "Email body is required.")
        if not cleaned_data.get("date_received"):
            self.add_error("date_received", "Date received is required.")
        return cleaned_data

    def save(self, commit=True):
        if not commit:
            raise ValueError(
                "RecruiterEmailImportForm must be saved with commit=True."
            )
        return create_recruiter_email_from_form_data(
            application=self.application,
            cleaned_data=self.cleaned_data,
        )
