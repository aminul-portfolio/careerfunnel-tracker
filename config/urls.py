from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", RedirectView.as_view(pattern_name="dashboard:overview", permanent=False)),
    path("dashboard/", include("apps.dashboard.urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("applications/", include("apps.applications.urls")),
    path("daily-log/", include("apps.daily_log.urls")),
    path("weekly-review/", include("apps.weekly_review.urls")),
    path("metrics/", include("apps.metrics.urls")),
    path("notes/", include("apps.notes.urls")),
    path("exports/", include("apps.exports.urls")),
    path("interviews/", include("apps.interviews.urls")),
    path("follow-ups/", include("apps.followups.urls")),
    path("smart-review/", include("apps.job_intelligence.urls")),
    path("ai-agents/", include("apps.ai_agents.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
