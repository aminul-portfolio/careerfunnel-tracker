from django.urls import path

from . import views

app_name = "skill_ledger"

urlpatterns = [
    path("", views.skill_ledger_list, name="list"),
    path("add/", views.skill_entry_create, name="create"),
    path("advisory/", views.skill_ledger_advisory, name="advisory"),
    path("public/", views.skill_ledger_public, name="public"),
    path("<int:pk>/edit/", views.skill_entry_edit, name="edit"),
    path("<int:pk>/", views.skill_entry_detail, name="detail"),
]
