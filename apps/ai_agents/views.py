from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render

from apps.applications.choices import DocumentType
from apps.applications.document_text_extraction import (
    resolve_cover_letter_for_check,
    resolve_cv_evidence_for_analysis,
)
from apps.applications.document_uploads import (
    attach_uploaded_document,
    extract_uploaded_document_text,
)
from apps.applications.models import JobApplication
from apps.job_intelligence.draft_documents import build_application_document_drafts_from_fields

from .claude_provider import make_claude_cv_tailoring_provider, make_claude_provider
from .forms import (
    ApplicationChoiceForm,
    CoverLetterQualityForm,
    CVGapAnalyzerForm,
    JobPostingAnalyzerForm,
)
from .services import (
    analyze_cv_gap,
    analyze_job_posting,
    analyze_rejection_patterns,
    build_cv_ab_testing_rows,
    build_cv_tailoring_advisor,
    build_next_best_actions,
    build_openai_fit_scoring_with_fallback,
    build_smart_notifications,
    build_weekly_coach_report,
    check_cover_letter_quality,
    compare_openai_wrapper_result_with_rule_based,
    count_weekly_reviews,
    generate_followup_message,
    generate_interview_prep,
    get_latest_weekly_review,
)


def _recruiter_email_has_interview_screening_signal(recruiter_email) -> bool:
    if recruiter_email is None or not recruiter_email.matched_signals:
        return False
    signals_text = recruiter_email.matched_signals.lower()
    return "interview" in signals_text or "screening" in signals_text


def _application_has_interview_recruiter_signal(application) -> bool:
    for recruiter_email in application.recruiter_emails.all():
        if _recruiter_email_has_interview_screening_signal(recruiter_email):
            return True
    return False


@login_required
def agent_dashboard(request):
    actions = build_next_best_actions(request.user, limit=5)
    return render(request, "ai_agents/agent_dashboard.html", {"actions": actions})


@login_required
def job_posting_analyzer(request):
    analysis = None
    tailoring_advisor = None
    ai_wrapper_result = None
    ai_score_comparison = None
    document_drafts = None
    if request.method == "POST":
        form = JobPostingAnalyzerForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data.get("company_name", "")
            job_title = form.cleaned_data.get("job_title", "")
            location = form.cleaned_data.get("location", "")
            job_posting = form.cleaned_data["job_posting"]
            analysis = analyze_job_posting(
                company_name=company_name,
                job_title=job_title,
                location=location,
                job_posting=job_posting,
            )
            if request.POST.get("generate_drafts"):
                document_drafts = build_application_document_drafts_from_fields(
                    company_name=company_name,
                    job_title=job_title,
                    location=location,
                    job_description=job_posting,
                    fit_score=analysis.fit_score,
                    fit_label=analysis.recommendation,
                    recommended_cv=analysis.recommended_cv,
                    recommended_projects=analysis.recommended_projects,
                )
            api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
            provider = make_claude_provider(api_key) if api_key else None
            ai_wrapper_result = build_openai_fit_scoring_with_fallback(
                company_name=company_name,
                job_title=job_title,
                location=location,
                job_description=job_posting,
                provider_callable=provider,
            )
            if ai_wrapper_result.ai_result is not None:
                ai_score_comparison = compare_openai_wrapper_result_with_rule_based(
                    analysis.fit_score,
                    ai_wrapper_result,
                )
            cv_tailoring_provider = (
                make_claude_cv_tailoring_provider(api_key) if api_key else None
            )
            tailoring_advisor = build_cv_tailoring_advisor(
                company_name=company_name,
                job_title=job_title,
                location=location,
                job_description=job_posting,
                cv_evidence="",
                provider_callable=cv_tailoring_provider,
            )
    else:
        form = JobPostingAnalyzerForm()
    return render(
        request,
        "ai_agents/job_posting_analyzer.html",
        {
            "form": form,
            "analysis": analysis,
            "tailoring_advisor": tailoring_advisor,
            "ai_wrapper_result": ai_wrapper_result,
            "ai_score_comparison": ai_score_comparison,
            "document_drafts": document_drafts,
        },
    )


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
    user = request.user
    report = build_weekly_coach_report(user)
    return render(
        request,
        "ai_agents/weekly_coach.html",
        {
            "report": report,
            "latest_weekly_review": get_latest_weekly_review(user),
            "weekly_review_count": count_weekly_reviews(user),
        },
    )


@login_required
def application_agent_pack(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, user=request.user)
    prep = generate_interview_prep(application)
    followup = generate_followup_message(application)
    analysis = analyze_job_posting(
        company_name=application.company_name,
        job_title=application.job_title,
        location=application.location,
        job_posting=" ".join(
            [application.required_skills, application.job_description, application.notes]
        ),
    )
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    cv_tailoring_provider = (
        make_claude_cv_tailoring_provider(api_key) if api_key else None
    )
    tailoring_advisor = build_cv_tailoring_advisor(
        company_name=application.company_name,
        job_title=application.job_title,
        location=application.location,
        job_description=" ".join(
            [application.required_skills, application.job_description, application.notes]
        ),
        cv_evidence=" ".join([application.cv_version, application.cover_letter_version]),
        provider_callable=cv_tailoring_provider,
    )
    interview_preps = application.interview_preps.all()[:5]
    latest_recruiter_email = application.recruiter_emails.first()
    has_interview_signal = _application_has_interview_recruiter_signal(application)
    return render(
        request,
        "ai_agents/application_agent_pack.html",
        {
            "application": application,
            "prep": prep,
            "followup": followup,
            "analysis": analysis,
            "tailoring_advisor": tailoring_advisor,
            "interview_preps": interview_preps,
            "latest_recruiter_email": latest_recruiter_email,
            "has_interview_signal": has_interview_signal,
        },
    )


@login_required
def cv_gap_analyzer(request):
    analysis = None
    upload_message = None
    uploaded_filename = None
    if request.method == "POST":
        action = request.POST.get("action", "analyze")
        form = CVGapAnalyzerForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            cv_file = form.cleaned_data.get("cv_file")
            application = form.cleaned_data.get("application")
            cv_evidence = form.cleaned_data.get("cv_evidence", "")

            if cv_file is not None:
                uploaded_filename = cv_file.name

            if action == "extract_cv_file" and cv_file is not None:
                extraction = extract_uploaded_document_text(cv_file)
                upload_message = extraction.status_message
                post_data = request.POST.copy()
                if extraction.extracted:
                    post_data["cv_evidence"] = extraction.text
                    cv_evidence = extraction.text
                form = CVGapAnalyzerForm(post_data, request.FILES, user=request.user)
                if application is not None:
                    try:
                        attach_uploaded_document(
                            application=application,
                            document_type=DocumentType.CV,
                            uploaded_file=cv_file,
                            content=extraction.text if extraction.extracted else "",
                        )
                        messages.success(
                            request,
                            "Uploaded Final CV saved to the application document pack.",
                        )
                    except ValidationError as exc:
                        messages.error(request, exc.messages[0])

            elif action == "analyze":
                resolution = resolve_cv_evidence_for_analysis(
                    pasted_text=cv_evidence,
                    uploaded_file=cv_file,
                )
                cv_evidence = resolution.text
                if resolution.status_message:
                    upload_message = resolution.status_message
                if resolution.validation_error:
                    messages.error(request, resolution.validation_error)
                elif cv_evidence:
                    analysis = analyze_cv_gap(
                        job_description=form.cleaned_data["job_description"],
                        cv_evidence=cv_evidence,
                    )
                if cv_file is not None and application is not None:
                    try:
                        extraction = extract_uploaded_document_text(cv_file)
                        attach_uploaded_document(
                            application=application,
                            document_type=DocumentType.CV,
                            uploaded_file=cv_file,
                            content=extraction.text if extraction.extracted else "",
                        )
                    except ValidationError as exc:
                        messages.error(request, exc.messages[0])
                post_data = request.POST.copy()
                post_data["cv_evidence"] = cv_evidence
                form = CVGapAnalyzerForm(post_data, request.FILES, user=request.user)
    else:
        form = CVGapAnalyzerForm(user=request.user)
    return render(
        request,
        "ai_agents/cv_gap_analyzer.html",
        {
            "form": form,
            "analysis": analysis,
            "upload_message": upload_message,
            "uploaded_filename": uploaded_filename,
        },
    )


@login_required
def cover_letter_quality_checker(request):
    result = None
    upload_message = None
    uploaded_filename = None
    if request.method == "POST":
        action = request.POST.get("action", "check")
        form = CoverLetterQualityForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            company_name = form.cleaned_data.get("company_name", "")
            job_title = form.cleaned_data.get("job_title", "")
            job_description = form.cleaned_data.get("job_description", "")
            cover_letter = form.cleaned_data.get("cover_letter", "")
            cover_letter_file = form.cleaned_data.get("cover_letter_file")
            application = form.cleaned_data.get("application")

            if cover_letter_file is not None:
                uploaded_filename = cover_letter_file.name

            if action == "extract_cover_letter_file" and cover_letter_file is not None:
                extraction = extract_uploaded_document_text(cover_letter_file)
                upload_message = extraction.status_message
                post_data = request.POST.copy()
                if extraction.extracted:
                    post_data["cover_letter"] = extraction.text
                    cover_letter = extraction.text
                form = CoverLetterQualityForm(post_data, request.FILES, user=request.user)
                if application is not None:
                    try:
                        attach_uploaded_document(
                            application=application,
                            document_type=DocumentType.COVER_LETTER,
                            uploaded_file=cover_letter_file,
                            content=extraction.text if extraction.extracted else "",
                        )
                        messages.success(
                            request,
                            "Uploaded Final Cover Letter saved to the application document pack.",
                        )
                    except ValidationError as exc:
                        messages.error(request, exc.messages[0])

            elif action == "upload_cover_letter_file" and cover_letter_file is not None:
                if application is None:
                    messages.error(
                        request,
                        "Select an application before uploading a cover letter file.",
                    )
                else:
                    try:
                        extraction = extract_uploaded_document_text(cover_letter_file)
                        upload_result = attach_uploaded_document(
                            application=application,
                            document_type=DocumentType.COVER_LETTER,
                            uploaded_file=cover_letter_file,
                            content=extraction.text if extraction.extracted else "",
                        )
                        upload_message = upload_result.message
                        messages.success(
                            request,
                            "Uploaded document saved for manual review. No check was run.",
                        )
                    except ValidationError as exc:
                        messages.error(request, exc.messages[0])

            elif action == "check":
                resolution = resolve_cover_letter_for_check(
                    pasted_text=cover_letter,
                    uploaded_file=cover_letter_file,
                )
                cover_letter = resolution.text
                if resolution.status_message and not upload_message:
                    upload_message = resolution.status_message
                post_data = request.POST.copy()
                post_data["cover_letter"] = cover_letter
                form = CoverLetterQualityForm(post_data, request.FILES, user=request.user)

                if resolution.validation_error:
                    messages.error(request, resolution.validation_error)
                else:
                    result = check_cover_letter_quality(
                        company_name=company_name,
                        job_title=job_title,
                        job_description=job_description,
                        cover_letter=cover_letter,
                    )
    else:
        form = CoverLetterQualityForm(user=request.user)
    return render(
        request,
        "ai_agents/cover_letter_quality_checker.html",
        {
            "form": form,
            "result": result,
            "upload_message": upload_message,
            "uploaded_filename": uploaded_filename,
        },
    )


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
