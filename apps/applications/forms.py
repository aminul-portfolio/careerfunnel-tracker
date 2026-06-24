from django import forms

from .choices import DocumentType
from .models import ApplicationDocument, JobApplication


class JobApplicationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["follow_up_status"].required = False

    class Meta:
        model = JobApplication
        fields = [
            "company_name",
            "job_title",
            "job_url",
            "location",
            "work_type",
            "salary_range",
            "source",
            "role_fit",
            "experience_level",
            "required_skills",
            "job_description",
            "date_applied",
            "status",
            "response_date",
            "cv_version",
            "cover_letter_version",
            "is_cv_tailored",
            "is_cover_letter_tailored",
            "portfolio_project_included",
            "company_researched",
            "follow_up_date",
            "follow_up_status",
            "last_contacted_date",
            "next_action",
            "contact_name",
            "contact_email",
            "notes",
        ]
        widgets = {
            "company_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Example: Monzo"}
            ),
            "job_title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Junior Data Analyst",
                }
            ),
            "job_url": forms.URLInput(
                attrs={"class": "form-control", "placeholder": "Paste job posting URL"}
            ),
            "location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "London / Remote UK / Hybrid London",
                }
            ),
            "work_type": forms.Select(attrs={"class": "form-control"}),
            "salary_range": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "£28,000 - £35,000"}
            ),
            "source": forms.Select(attrs={"class": "form-control"}),
            "role_fit": forms.Select(attrs={"class": "form-control"}),
            "experience_level": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Graduate / Junior / 0-2 years",
                }
            ),
            "required_skills": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Python, SQL, Excel, Power BI, reporting...",
                }
            ),
            "job_description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Paste short job description or key requirements.",
                }
            ),
            "date_applied": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "status": forms.Select(attrs={"class": "form-control"}),
            "response_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "cv_version": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Aminul_Islam_Data_Analyst_CV"}
            ),
            "cover_letter_version": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Tailored_CL_v1"}
            ),
            "is_cv_tailored": forms.CheckboxInput(attrs={"class": "checkbox-input"}),
            "is_cover_letter_tailored": forms.CheckboxInput(attrs={"class": "checkbox-input"}),
            "portfolio_project_included": forms.CheckboxInput(attrs={"class": "checkbox-input"}),
            "company_researched": forms.CheckboxInput(attrs={"class": "checkbox-input"}),
            "follow_up_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "follow_up_status": forms.Select(attrs={"class": "form-control"}),
            "last_contacted_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
            "next_action": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: Send follow-up / prepare interview walkthrough",
                }
            ),
            "contact_name": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Recruiter name"}
            ),
            "contact_email": forms.EmailInput(
                attrs={"class": "form-control", "placeholder": "Recruiter email"}
            ),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def clean(self):
        cleaned_data = super().clean()
        date_applied = cleaned_data.get("date_applied")
        response_date = cleaned_data.get("response_date")
        follow_up_date = cleaned_data.get("follow_up_date")

        if not cleaned_data.get("follow_up_status"):
            cleaned_data["follow_up_status"] = "not_set"

        if response_date and date_applied and response_date < date_applied:
            self.add_error("response_date", "Response date cannot be before the application date.")

        if follow_up_date and date_applied and follow_up_date < date_applied:
            self.add_error(
                "follow_up_date",
                "Follow-up date cannot be before the application date.",
            )

        return cleaned_data


class ApplicationStatusUpdateForm(forms.ModelForm):
    status_note = forms.CharField(
        required=False,
        help_text=(
            "Optional - appended to your existing notes with a timestamp. "
            "Previous notes are not deleted."
        ),
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 4}),
    )

    class Meta:
        model = JobApplication
        fields = ["status", "pipeline_stage", "response_date"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-control"}),
            "pipeline_stage": forms.Select(attrs={"class": "form-control"}),
            "response_date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"class": "form-control", "type": "date"},
            ),
        }

    def clean(self):
        cleaned_data = super().clean()
        response_date = cleaned_data.get("response_date")
        date_applied = self.instance.date_applied if self.instance else None
        if response_date and date_applied and response_date < date_applied:
            self.add_error(
                "response_date",
                "Response date cannot be before the application date.",
            )
        return cleaned_data


class ExternalDocumentReferenceForm(forms.Form):
    name = forms.CharField(
        max_length=255,
        required=True,
        label="Version / name",
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Notes",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["class"] = "form-control"
        self.fields["notes"].widget.attrs["class"] = "form-control"


class DocumentPackUploadForm(forms.Form):
    uploaded_file = forms.FileField(
        required=True,
        label="Document file",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["uploaded_file"].widget.attrs["class"] = "form-control"
        self.fields["uploaded_file"].widget.attrs["accept"] = ".pdf,.docx"

    def clean_uploaded_file(self):
        from apps.applications.document_uploads import validate_document_pack_upload

        uploaded_file = self.cleaned_data["uploaded_file"]
        validate_document_pack_upload(uploaded_file)
        return uploaded_file


class ApplicationDocumentSelectionForm(forms.Form):
    selected_cv_document = forms.ModelChoiceField(
        queryset=ApplicationDocument.objects.none(),
        required=False,
        empty_label="No CV selected",
        label="CV document",
    )
    selected_cover_letter_document = forms.ModelChoiceField(
        queryset=ApplicationDocument.objects.none(),
        required=False,
        empty_label="No cover letter selected",
        label="Cover-letter document",
    )

    def __init__(self, *args, application=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.application = application
        if application is not None:
            self.fields["selected_cv_document"].queryset = ApplicationDocument.objects.filter(
                application=application,
                document_type=DocumentType.CV,
            )
            self.fields["selected_cover_letter_document"].queryset = (
                ApplicationDocument.objects.filter(
                    application=application,
                    document_type=DocumentType.COVER_LETTER,
                )
            )
        for field_name in ("selected_cv_document", "selected_cover_letter_document"):
            self.fields[field_name].widget.attrs["class"] = "form-control"

    def clean(self):
        cleaned_data = super().clean()
        if self.application is None:
            return cleaned_data

        cv_document = cleaned_data.get("selected_cv_document")
        cover_letter_document = cleaned_data.get("selected_cover_letter_document")
        validations = (
            (cv_document, DocumentType.CV, "selected_cv_document"),
            (
                cover_letter_document,
                DocumentType.COVER_LETTER,
                "selected_cover_letter_document",
            ),
        )
        for document, expected_type, field_name in validations:
            if document is None:
                continue
            if document.application_id != self.application.pk:
                self.add_error(field_name, "Document must belong to this application.")
            elif document.document_type != expected_type:
                self.add_error(field_name, "Invalid document type for this field.")
        return cleaned_data
