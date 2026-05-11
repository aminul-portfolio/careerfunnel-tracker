from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("", views.application_list, name="application_list"),
    path("add/", views.application_create, name="application_create"),
    path("<int:pk>/", views.application_detail, name="application_detail"),
    path("<int:pk>/edit/", views.application_update, name="application_update"),
    path("<int:pk>/delete/", views.application_delete, name="application_delete"),
]
