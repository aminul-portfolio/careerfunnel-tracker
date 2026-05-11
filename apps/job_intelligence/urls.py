from django.urls import path

from . import views

app_name = "job_intelligence"

urlpatterns = [
    path("", views.smart_review, name="smart_review"),
    path("<int:pk>/", views.application_smart_review, name="application_smart_review"),
]
