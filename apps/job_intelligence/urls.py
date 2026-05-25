from django.urls import path

from . import views

app_name = "job_intelligence"

urlpatterns = [
    path("", views.smart_review, name="smart_review"),
    path("skill-intelligence/", views.skill_intelligence, name="skill_intelligence"),
    path("<int:pk>/", views.application_smart_review, name="application_smart_review"),
]
