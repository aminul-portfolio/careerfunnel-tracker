from django.urls import path

from .views import (
    UserLoginView,
    UserLogoutView,
    UserPasswordChangeView,
    profile_view,
    register_view,
    settings_view,
)

app_name = "accounts"

urlpatterns = [
    path("login/", UserLoginView.as_view(), name="login"),
    path("logout/", UserLogoutView.as_view(), name="logout"),
    path("register/", register_view, name="register"),
    path("profile/", profile_view, name="profile"),
    path("settings/", settings_view, name="settings"),
    path("password/change/", UserPasswordChangeView.as_view(), name="password_change"),
]
