from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import build_dashboard_context


@login_required
def overview(request):
    return render(request, "dashboard/overview.html", build_dashboard_context(request.user))
