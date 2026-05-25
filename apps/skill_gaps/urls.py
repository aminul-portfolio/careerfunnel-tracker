from django.urls import path

from . import views

app_name = "skill_gaps"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
]
