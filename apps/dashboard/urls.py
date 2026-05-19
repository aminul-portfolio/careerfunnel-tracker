from django.urls import path

from . import views
from .views import career_evidence_views

app_name = "dashboard"

urlpatterns = [
    path("", views.overview, name="overview"),
    path(
        "career-evidence/",
        career_evidence_views.career_evidence_index,
        name="career_evidence_index",
    ),
    path(
        "career-evidence/project-evidence/",
        career_evidence_views.project_evidence_detail,
        name="career_evidence_project",
    ),
    path(
        "career-evidence/job-fit-matrix/",
        career_evidence_views.job_fit_matrix_detail,
        name="career_evidence_job_fit",
    ),
    path(
        "career-evidence/recruiter-pack/",
        career_evidence_views.recruiter_pack_detail,
        name="career_evidence_recruiter",
    ),
]
