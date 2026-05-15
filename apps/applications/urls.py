from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("", views.application_list, name="application_list"),
    path("add/", views.application_create, name="application_create"),
    path("evaluation/", views.evaluation_queue, name="evaluation_queue"),
    path("<int:pk>/", views.application_detail, name="application_detail"),
    path(
        "<int:pk>/mark-followup-sent/",
        views.application_mark_followup_sent,
        name="application_mark_followup_sent",
    ),
    path("<int:pk>/edit/", views.application_update, name="application_update"),
    path("<int:pk>/delete/", views.application_delete, name="application_delete"),
]
