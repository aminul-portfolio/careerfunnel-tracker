"""Transient JD Gap Analysis form (Sprint 110B Phase 2)."""

from django import forms

from .deterministic_gap_classifier import normalise_requirement

MAX_RAW_LENGTH = 6000
MAX_ACCEPTED_LINES = 30
MAX_LINE_LENGTH = 300


class JDGapAnalysisForm(forms.Form):
    requirements = forms.CharField(
        label="Job requirements",
        help_text=(
            "Enter one atomic job requirement per line. Use no more than 30 lines and "
            "300 characters per line."
        ),
        widget=forms.Textarea(
            attrs={
                "rows": 12,
                "class": "form-control",
                "aria-label": "Job requirements",
            }
        ),
        strip=False,
        max_length=MAX_RAW_LENGTH,
        required=True,
    )

    def clean_requirements(self):
        raw_value = self.cleaned_data.get("requirements", "")
        if raw_value is None:
            raw_value = ""
        if len(raw_value) > MAX_RAW_LENGTH:
            raise forms.ValidationError(
                f"Requirements must be at most {MAX_RAW_LENGTH} characters."
            )

        accepted_lines: list[str] = []
        for line in raw_value.splitlines():
            trimmed = line.strip()
            if not trimmed:
                continue
            if len(trimmed) > MAX_LINE_LENGTH:
                raise forms.ValidationError(
                    f"Each requirement line must be at most {MAX_LINE_LENGTH} characters."
                )
            accepted_lines.append(trimmed)

        if not accepted_lines:
            raise forms.ValidationError(
                "Enter at least one non-blank job requirement line."
            )
        if len(accepted_lines) > MAX_ACCEPTED_LINES:
            raise forms.ValidationError(
                f"Enter at most {MAX_ACCEPTED_LINES} non-blank requirement lines."
            )

        normalised_requirements = []
        seen_keys: set[str] = set()
        for index, accepted_line in enumerate(accepted_lines):
            requirement = normalise_requirement(index, accepted_line)
            if not requirement.normalised_text:
                raise forms.ValidationError(
                    "Each requirement line must contain a usable skill or requirement "
                    "after marker removal."
                )
            if requirement.normalised_text in seen_keys:
                raise forms.ValidationError(
                    "Duplicate requirements are not allowed after normalisation. "
                    "Each accepted line must resolve to a distinct requirement."
                )
            seen_keys.add(requirement.normalised_text)
            normalised_requirements.append(requirement)

        self.cleaned_data["normalised_requirements"] = tuple(normalised_requirements)
        return raw_value

    def clean(self):
        cleaned = super().clean()
        # Ensure normalised_requirements is available even if field clean already ran.
        if (
            "requirements" in cleaned
            and "normalised_requirements" not in cleaned
            and "normalised_requirements" in self.cleaned_data
        ):
            cleaned["normalised_requirements"] = self.cleaned_data[
                "normalised_requirements"
            ]
        return cleaned
