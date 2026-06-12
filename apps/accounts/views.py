from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView, PasswordChangeView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import AccountSettingsForm, LoginForm, PremiumPasswordChangeForm, RegisterForm
from .services import build_account_profile_context, build_account_settings_context


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if request.method == "POST" and request.user.is_authenticated:
            messages.info(
                request,
                "Signed out. Your portfolio workspace session has ended.",
            )
        return super().dispatch(request, *args, **kwargs)


class UserPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:settings")
    form_class = PremiumPasswordChangeForm


@login_required
def profile_view(request):
    profile = build_account_profile_context(request.user)
    return render(
        request,
        "accounts/profile.html",
        {
            "profile": profile,
            "page_title": "Profile",
        },
    )


@login_required
def settings_view(request):
    settings_context = build_account_settings_context(request.user)
    if request.method == "POST":
        form = AccountSettingsForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Account settings saved.")
            return redirect("accounts:settings")
    else:
        form = AccountSettingsForm(instance=request.user)

    return render(
        request,
        "accounts/settings.html",
        {
            "form": form,
            "settings_context": settings_context,
            "page_title": "Settings",
        },
    )


def register_view(request):
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})
