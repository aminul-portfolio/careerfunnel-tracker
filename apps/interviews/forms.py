from django import forms

from .models import InterviewPrep


class InterviewPrepForm(forms.ModelForm):
    class Meta:
        model = InterviewPrep
        fields = [
            "application",
            "interview_date",
            "stage",
            "outcome",
            "interviewer_names",
            "expected_topics",
            "projects_to_mention",
            "questions_to_prepare",
            "profile_answer_prepared",
            "company_answer_prepared",
            "project_walkthrough_prepared",
            "sql_practice_done",
            "python_practice_done",
            "star_examples_prepared",
            "questions_for_employer_prepared",
            "reflection",
        ]
        widgets = {
            "application": forms.Select(attrs={"class": "form-control"}),
            "interview_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "stage": forms.Select(attrs={"class": "form-control"}),
            "outcome": forms.Select(attrs={"class": "form-control"}),
            "interviewer_names": forms.TextInput(attrs={"class": "form-control"}),
            "expected_topics": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "projects_to_mention": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "questions_to_prepare": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "reflection": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["application"].queryset = self.fields["application"].queryset.filter(
                user=user
            )
