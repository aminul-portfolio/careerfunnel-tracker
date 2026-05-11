from django.urls import path

from . import views

app_name = "followups"

urlpatterns = [
    path("", views.followup_list, name="followup_list"),
    path("<int:pk>/mark-sent/", views.mark_sent, name="mark_sent"),
]
