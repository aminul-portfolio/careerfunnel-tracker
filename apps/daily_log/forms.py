from django import forms

from .models import DailyLog


class DailyLogForm(forms.ModelForm):
    class Meta:
        model = DailyLog
        fields = [
            "log_date",
            "target_applications",
            "actual_applications",
            "cover_letters_drafted",
            "responses_received",
            "calls_received",
            "hours_spent",
            "energy_level",
            "notes",
        ]
        widgets = {
            "log_date": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "target_applications": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "actual_applications": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "cover_letters_drafted": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "responses_received": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "calls_received": forms.NumberInput(attrs={"class": "form-control", "min": 0}),
            "hours_spent": forms.NumberInput(
                attrs={"class": "form-control", "min": 0, "step": "0.25"}
            ),
            "energy_level": forms.NumberInput(attrs={"class": "form-control", "min": 1, "max": 5}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 5}),
        }

    def clean_energy_level(self):
        energy_level = self.cleaned_data["energy_level"]
        if energy_level < 1 or energy_level > 5:
            raise forms.ValidationError("Energy level must be between 1 and 5.")
        return energy_level
