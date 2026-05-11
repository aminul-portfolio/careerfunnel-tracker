from django.urls import path

from . import views

app_name = "weekly_review"

urlpatterns = [
    path("", views.weekly_review_list, name="weekly_review_list"),
    path("add/", views.weekly_review_create, name="weekly_review_create"),
    path("<int:pk>/", views.weekly_review_detail, name="weekly_review_detail"),
    path("<int:pk>/edit/", views.weekly_review_update, name="weekly_review_update"),
    path("<int:pk>/delete/", views.weekly_review_delete, name="weekly_review_delete"),
]
