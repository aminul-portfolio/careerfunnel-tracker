from django.contrib.auth import login
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm


class UserLogoutView(LogoutView):
    pass


def register_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard:overview")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("dashboard:overview")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})
