from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from apps.applications.models import JobApplication

from .forms import ApplicationChoiceForm, CoverLetterQualityForm, CVGapAnalyzerForm, JobPostingAnalyzerForm
from .services import (
    analyze_job_posting,
    build_next_best_actions,
    build_weekly_coach_report,
    build_cv_ab_testing_rows,
    build_smart_notifications,
    analyze_cv_gap,
    analyze_rejection_patterns,
    check_cover_letter_quality,
    generate_followup_message,
    generate_interview_prep,
)


@login_required
def agent_dashboard(request):
    actions = build_next_best_actions(request.user, limit=5)
    return render(request, "ai_agents/agent_dashboard.html", {"actions": actions})


@login_required
def job_posting_analyzer(request):
    analysis = None
    if request.method == "POST":
        form = JobPostingAnalyzerForm(request.POST)
        if form.is_valid():
            analysis = analyze_job_posting(
                company_name=form.cleaned_data.get("company_name", ""),
                job_title=form.cleaned_data.get("job_title", ""),
                location=form.cleaned_data.get("location", ""),
                job_posting=form.cleaned_data["job_posting"],
            )
    else:
        form = JobPostingAnalyzerForm()
    return render(request, "ai_agents/job_posting_analyzer.html", {"form": form, "analysis": analysis})


@login_required
def next_best_actions(request):
    actions = build_next_best_actions(request.user, limit=12)
    return render(request, "ai_agents/next_best_actions.html", {"actions": actions})


@login_required
def followup_writer(request):
    draft = None
    selected_application = None
    if request.method == "POST":
        form = ApplicationChoiceForm(request.POST, user=request.user)
        if form.is_valid():
            selected_application = form.cleaned_data["application"]
            draft = generate_followup_message(selected_application)
    else:
        form = ApplicationChoiceForm(user=request.user)
    return render(
        request,
        "ai_agents/followup_writer.html",
        {"form": form, "draft": draft, "selected_application": selected_application},
    )


@login_required
def interview_prep_generator(request):
    prep = None
    selected_application = None
    if request.method == "POST":
        form = ApplicationChoiceForm(request.POST, user=request.user)
        if form.is_valid():
            selected_application = form.cleaned_data["application"]
            prep = generate_interview_prep(selected_application)
    else:
        form = ApplicationChoiceForm(user=request.user)
    return render(
        request,
        "ai_agents/interview_prep_generator.html",
        {"form": form, "prep": prep, "selected_application": selected_application},
    )


@login_required
def weekly_coach(request):
    report = build_weekly_coach_report(request.user)
    return render(request, "ai_agents/weekly_coach.html", {"report": report})


@login_required
def application_agent_pack(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    prep = generate_interview_prep(application)
    followup = generate_followup_message(application)
    analysis = analyze_job_posting(
        company_name=application.company_name,
        job_title=application.job_title,
        location=application.location,
        job_posting=" ".join([application.required_skills, application.job_description, application.notes]),
    )
    return render(
        request,
        "ai_agents/application_agent_pack.html",
        {"application": application, "prep": prep, "followup": followup, "analysis": analysis},
    )


@login_required
def cv_gap_analyzer(request):
    analysis = None
    if request.method == "POST":
        form = CVGapAnalyzerForm(request.POST)
        if form.is_valid():
            analysis = analyze_cv_gap(
                job_description=form.cleaned_data["job_description"],
                cv_evidence=form.cleaned_data.get("cv_evidence", ""),
            )
    else:
        form = CVGapAnalyzerForm()
    return render(request, "ai_agents/cv_gap_analyzer.html", {"form": form, "analysis": analysis})


@login_required
def cover_letter_quality_checker(request):
    result = None
    if request.method == "POST":
        form = CoverLetterQualityForm(request.POST)
        if form.is_valid():
            result = check_cover_letter_quality(
                company_name=form.cleaned_data.get("company_name", ""),
                job_title=form.cleaned_data.get("job_title", ""),
                job_description=form.cleaned_data.get("job_description", ""),
                cover_letter=form.cleaned_data["cover_letter"],
            )
    else:
        form = CoverLetterQualityForm()
    return render(request, "ai_agents/cover_letter_quality_checker.html", {"form": form, "result": result})


@login_required
def rejection_pattern_analyzer(request):
    report = analyze_rejection_patterns(request.user)
    return render(request, "ai_agents/rejection_pattern_analyzer.html", {"report": report})


@login_required
def cv_ab_testing(request):
    rows = build_cv_ab_testing_rows(request.user)
    return render(request, "ai_agents/cv_ab_testing.html", {"rows": rows})


@login_required
def smart_notifications(request):
    notifications = build_smart_notifications(request.user)
    return render(request, "ai_agents/smart_notifications.html", {"notifications": notifications})
