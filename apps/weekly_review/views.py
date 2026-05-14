from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import WeeklyReviewForm
from .models import WeeklyReview
from .services import (
    build_weekly_review_summary,
    build_weekly_review_table_rows,
    get_diagnosis_badge_class,
    get_variance_badge_class,
)


@login_required
def weekly_review_list(request):
    reviews = WeeklyReview.objects.filter(user=request.user)
    return render(
        request,
        "weekly_review/weekly_review_list.html",
        {
            "reviews": reviews,
            "table_rows": build_weekly_review_table_rows(reviews),
            "summary": build_weekly_review_summary(request.user),
        },
    )


@login_required
def weekly_review_detail(request, pk):
    review = get_object_or_404(WeeklyReview, pk=pk, user=request.user)
    return render(
        request,
        "weekly_review/weekly_review_detail.html",
        {
            "review": review,
            "variance_badge_class": get_variance_badge_class(
                review.application_variance
            ),
            "diagnosis_badge_class": get_diagnosis_badge_class(review.diagnosis),
        },
    )


@login_required
def weekly_review_create(request):
    if request.method == "POST":
        form = WeeklyReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            try:
                review.save()
            except IntegrityError:
                form.add_error(
                    "week_ending",
                    "You already have a weekly review for this week ending date. "
                    "Edit the existing review instead.",
                )
            else:
                messages.success(request, "Weekly review created successfully.")
                return redirect(review.get_absolute_url())
    else:
        form = WeeklyReviewForm()
    return render(
        request,
        "weekly_review/weekly_review_form.html",
        {
            "form": form,
            "page_title": "Add Weekly Review",
            "submit_label": "Save Weekly Review",
        },
    )


@login_required
def weekly_review_update(request, pk):
    review = get_object_or_404(WeeklyReview, pk=pk, user=request.user)
    if request.method == "POST":
        form = WeeklyReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Weekly review updated successfully.")
            return redirect(review.get_absolute_url())
    else:
        form = WeeklyReviewForm(instance=review)
    return render(
        request,
        "weekly_review/weekly_review_form.html",
        {
            "form": form,
            "page_title": "Edit Weekly Review",
            "submit_label": "Update Weekly Review",
            "review": review,
        },
    )


@login_required
def weekly_review_delete(request, pk):
    review = get_object_or_404(WeeklyReview, pk=pk, user=request.user)
    if request.method == "POST":
        review.delete()
        messages.success(request, "Weekly review deleted successfully.")
        return redirect("weekly_review:weekly_review_list")
    return render(request, "weekly_review/weekly_review_confirm_delete.html", {"review": review})
