from django.urls import path

from . import views

app_name = "daily_log"

urlpatterns = [
    path("", views.daily_log_list, name="daily_log_list"),
    path("add/", views.daily_log_create, name="daily_log_create"),
    path("<int:pk>/", views.daily_log_detail, name="daily_log_detail"),
    path("<int:pk>/edit/", views.daily_log_update, name="daily_log_update"),
    path("<int:pk>/delete/", views.daily_log_delete, name="daily_log_delete"),
]
