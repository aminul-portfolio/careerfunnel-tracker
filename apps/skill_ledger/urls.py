from django.urls import path

from . import views

app_name = "skill_ledger"

urlpatterns = [
    path("", views.skill_ledger_list, name="list"),
    path("add/", views.skill_entry_create, name="create"),
    path("advisory/", views.skill_ledger_advisory, name="advisory"),
    path(
        "advisory/explanations/",
        views.skill_ledger_advisory_explanations,
        name="advisory_explanations",
    ),
    path(
        "advisory/ai-evidence/",
        views.skill_ledger_advisory_ai_evidence,
        name="advisory_ai_evidence",
    ),
    path(
        "advisory/ai-review-hub/",
        views.skill_ledger_advisory_ai_review_hub,
        name="advisory_ai_review_hub",
    ),
    path(
        "advisory/evaluation-casebook/",
        views.advisory_evaluation_casebook,
        name="advisory_evaluation_casebook",
    ),
    path(
        "advisory/manual-review-checklist/",
        views.skill_ledger_advisory_manual_review_checklist,
        name="advisory_manual_review_checklist",
    ),
    path("public/", views.skill_ledger_public, name="public"),
    path("<int:pk>/edit/", views.skill_entry_edit, name="edit"),
    path("<int:pk>/", views.skill_entry_detail, name="detail"),
]
