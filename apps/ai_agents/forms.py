from django import forms

from apps.applications.models import JobApplication


class JobPostingAnalyzerForm(forms.Form):
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Company name, if known"}),
    )
    job_title = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Example: Junior Data Analyst"}),
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Example: Hybrid London / Remote UK"}),
    )
    job_posting = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 12,
                "placeholder": "Paste the job description, requirements, responsibilities, and salary/location details here...",
            }
        )
    )


class ApplicationChoiceForm(forms.Form):
    application = forms.ModelChoiceField(
        queryset=JobApplication.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["application"].queryset = JobApplication.objects.filter(user=user).order_by(
                "-date_applied", "-created_at"
            )


class CVGapAnalyzerForm(forms.Form):
    job_description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 10,
                "placeholder": "Paste the job description, requirements, skills, and responsibilities here...",
            }
        )
    )
    cv_evidence = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 8,
                "placeholder": "Optional: paste your CV summary, skills section, project evidence, or cover-letter evidence here...",
            }
        ),
    )


class CoverLetterQualityForm(forms.Form):
    company_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Company name"}),
    )
    job_title = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Role title"}),
    )
    job_description = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 7, "placeholder": "Paste relevant job requirements here..."}),
    )
    cover_letter = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 12, "placeholder": "Paste your cover letter draft here..."})
    )
