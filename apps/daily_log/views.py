from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import DailyLogForm
from .models import DailyLog
from .services import build_daily_log_summary, build_daily_log_table_rows


@login_required
def daily_log_list(request):
    logs = DailyLog.objects.filter(user=request.user)
    return render(request, "daily_log/daily_log_list.html", {"logs": logs, "table_rows": build_daily_log_table_rows(logs), "summary": build_daily_log_summary(request.user)})


@login_required
def daily_log_detail(request, pk):
    log = get_object_or_404(DailyLog, pk=pk, user=request.user)
    return render(request, "daily_log/daily_log_detail.html", {"log": log})


@login_required
def daily_log_create(request):
    if request.method == "POST":
        form = DailyLogForm(request.POST)
        if form.is_valid():
            log = form.save(commit=False)
            log.user = request.user
            try:
                log.save()
            except IntegrityError:
                form.add_error("log_date", "You already have a daily log for this date. Edit the existing log instead.")
            else:
                messages.success(request, "Daily log created successfully.")
                return redirect(log.get_absolute_url())
    else:
        form = DailyLogForm()
    return render(request, "daily_log/daily_log_form.html", {"form": form, "page_title": "Add Daily Log", "submit_label": "Save Daily Log"})


@login_required
def daily_log_update(request, pk):
    log = get_object_or_404(DailyLog, pk=pk, user=request.user)
    if request.method == "POST":
        form = DailyLogForm(request.POST, instance=log)
        if form.is_valid():
            form.save()
            messages.success(request, "Daily log updated successfully.")
            return redirect(log.get_absolute_url())
    else:
        form = DailyLogForm(instance=log)
    return render(request, "daily_log/daily_log_form.html", {"form": form, "page_title": "Edit Daily Log", "submit_label": "Update Daily Log", "log": log})


@login_required
def daily_log_delete(request, pk):
    log = get_object_or_404(DailyLog, pk=pk, user=request.user)
    if request.method == "POST":
        log.delete()
        messages.success(request, "Daily log deleted successfully.")
        return redirect("daily_log:daily_log_list")
    return render(request, "daily_log/daily_log_confirm_delete.html", {"log": log})
