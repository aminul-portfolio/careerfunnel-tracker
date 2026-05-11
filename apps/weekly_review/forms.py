from django import forms

from .models import WeeklyReview


class WeeklyReviewForm(forms.ModelForm):
    class Meta:
        model = WeeklyReview
        fields = ["week_starting", "week_ending", "target_applications", "actual_applications", "responses_received", "screening_calls", "technical_screens", "interviews", "offers", "rejections", "diagnosis", "mood", "what_worked", "what_blocked", "lessons_learned", "change_next_week"]
        widgets = {
            "week_starting": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "week_ending": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "target_applications": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "actual_applications": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "responses_received": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "screening_calls": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "technical_screens": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "interviews": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "offers": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "rejections": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "diagnosis": forms.Select(attrs={"class": "form-control"}),
            "mood": forms.Select(attrs={"class": "form-control"}),
            "what_worked": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "what_blocked": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "lessons_learned": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "change_next_week": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
        }

    def clean(self):
        cleaned_data = super().clean()
        week_starting = cleaned_data.get("week_starting")
        week_ending = cleaned_data.get("week_ending")
        if week_starting and week_ending and week_ending < week_starting:
            self.add_error("week_ending", "Week ending date cannot be before week starting date.")
        return cleaned_data
