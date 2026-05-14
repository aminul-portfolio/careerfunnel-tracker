from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from .services import (
    build_applications_workbook,
    build_daily_logs_workbook,
    build_full_tracker_workbook,
    build_interviews_workbook,
    build_notes_workbook,
    build_weekly_reviews_workbook,
)


def build_excel_response(file_bytes: bytes, filename: str) -> HttpResponse:
    response = HttpResponse(
        file_bytes,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def dated_filename(prefix: str) -> str:
    return f"{prefix}_{timezone.localdate().strftime('%Y-%m-%d')}.xlsx"


@login_required
def export_center(request):
    return render(request, "exports/export_center.html")


@login_required
def export_applications(request):
    return build_excel_response(
        build_applications_workbook(request.user),
        dated_filename("careerfunnel_applications"),
    )


@login_required
def export_daily_logs(request):
    return build_excel_response(
        build_daily_logs_workbook(request.user),
        dated_filename("careerfunnel_daily_logs"),
    )


@login_required
def export_weekly_reviews(request):
    return build_excel_response(
        build_weekly_reviews_workbook(request.user),
        dated_filename("careerfunnel_weekly_reviews"),
    )


@login_required
def export_interviews(request):
    file_bytes = build_interviews_workbook(request.user)
    filename = dated_filename("careerfunnel_interview_prep")
    return build_excel_response(file_bytes, filename)


@login_required
def export_notes(request):
    return build_excel_response(
        build_notes_workbook(request.user),
        dated_filename("careerfunnel_notes_decisions"),
    )


@login_required
def export_full_tracker(request):
    return build_excel_response(
        build_full_tracker_workbook(request.user),
        dated_filename("careerfunnel_full_tracker"),
    )
