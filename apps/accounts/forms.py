from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.contrib.auth.models import User

PREMIUM_INPUT_CLASS = "form-control premium-input"
PREMIUM_FIELD_WRAPPER = "form-field form-group"


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(
            attrs={
                "class": PREMIUM_INPUT_CLASS,
                "placeholder": "Enter your username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": PREMIUM_INPUT_CLASS,
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "class": PREMIUM_INPUT_CLASS,
                "placeholder": "Enter your email",
                "autocomplete": "email",
            }
        ),
    )

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]
        widgets = {
            "username": forms.TextInput(
                attrs={
                    "class": PREMIUM_INPUT_CLASS,
                    "placeholder": "Choose a username",
                    "autocomplete": "username",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].widget.attrs.update(
            {
                "class": PREMIUM_INPUT_CLASS,
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        )
        self.fields["password2"].widget.attrs.update(
            {
                "class": PREMIUM_INPUT_CLASS,
                "placeholder": "Confirm your password",
                "autocomplete": "new-password",
            }
        )


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(
                attrs={"class": PREMIUM_INPUT_CLASS, "placeholder": "First name"}
            ),
            "last_name": forms.TextInput(
                attrs={"class": PREMIUM_INPUT_CLASS, "placeholder": "Last name"}
            ),
            "email": forms.EmailInput(
                attrs={"class": PREMIUM_INPUT_CLASS, "placeholder": "Email address"}
            ),
        }


class PremiumPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update(
                {"class": PREMIUM_INPUT_CLASS, "autocomplete": "new-password"}
            )
        self.fields["old_password"].widget.attrs["autocomplete"] = "current-password"
