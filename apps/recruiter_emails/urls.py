from django.urls import path

from . import views

app_name = "recruiter_emails"

urlpatterns = [
    path(
        "import/<int:application_id>/",
        views.import_recruiter_email,
        name="import",
    ),
    path("<int:pk>/", views.recruiter_email_detail, name="detail"),
    path(
        "<int:pk>/mark-sent/",
        views.mark_recruiter_email_sent,
        name="mark_sent",
    ),
]
