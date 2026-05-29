from django.urls import path

from . import views

app_name = "skills"

urlpatterns = [
    path(
        "ai-capability-framework/",
        views.ai_capability_framework,
        name="ai_capability_framework",
    ),
]
