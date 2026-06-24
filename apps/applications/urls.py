from django.urls import path

from . import views

app_name = "applications"

urlpatterns = [
    path("", views.application_list, name="application_list"),
    path("add/", views.application_create, name="application_create"),
    path(
        "data-quality/",
        views.application_data_quality_audit,
        name="application_data_quality_audit",
    ),
    path(
        "jd-gap-aggregation/",
        views.jd_gap_aggregation,
        name="jd_gap_aggregation",
    ),
    path("evaluation/", views.evaluation_queue, name="evaluation_queue"),
    path(
        "<int:pk>/evaluation/download/cv/<str:file_format>/",
        views.evaluation_cv_download,
        name="evaluation_cv_download",
    ),
    path(
        "<int:pk>/evaluation/download/cover-letter/<str:file_format>/",
        views.evaluation_cover_letter_download,
        name="evaluation_cover_letter_download",
    ),
    path(
        "<int:pk>/evaluation/download/application-pack/<str:file_format>/",
        views.evaluation_application_pack_download,
        name="evaluation_application_pack_download",
    ),
    path(
        "<int:pk>/update-status/",
        views.application_status_update,
        name="application_status_update",
    ),
    path("<int:pk>/", views.application_detail, name="application_detail"),
    path(
        "<int:pk>/documents/<int:document_pk>/download/<str:file_format>/",
        views.application_document_download,
        name="application_document_download",
    ),
    path(
        "<int:pk>/mark-followup-sent/",
        views.application_mark_followup_sent,
        name="application_mark_followup_sent",
    ),
    path("<int:pk>/edit/", views.application_update, name="application_update"),
    path("<int:pk>/delete/", views.application_delete, name="application_delete"),
]
