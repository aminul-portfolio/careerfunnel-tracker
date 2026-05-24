from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.applications.choices import ApplicationStatus, FollowUpStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.interviews.models import InterviewPrep
from apps.job_intelligence.constants import (
    DEAL_BREAKERS,
    GOOD_LOCATION_WORDS,
    GOOD_SKILLS,
    LEARNING_TARGETS,
    SENIOR_SIGNALS,
    TARGET_TITLES,
    TARGET_TITLES_AE_STRETCH,
)
from apps.metrics.services import build_funnel_metrics, diagnose_funnel, safe_percentage
from apps.weekly_review.models import WeeklyReview

LOCKED_CV = "Aminul_Islam_Data_Analyst_CV"


@dataclass(frozen=True)
class JobPostingAnalysis:
    fit_score: int
    recommendation: str
    severity: str
    matched_skills: list[str]
    risks: list[str]
    deal_breakers: list[str]
    recommended_cv: str
    recommended_projects: list[str]
    cover_letter_focus: list[str]
    next_actions: list[str]
    explanation: str


@dataclass(frozen=True)
class AgentAction:
    priority: str
    title: str
    reason: str
    recommended_action: str
    related_url: str | None = None


@dataclass(frozen=True)
class FollowUpDraft:
    subject: str
    body: str
    reason: str


@dataclass(frozen=True)
class InterviewPrepPack:
    profile_angle: str
    projects_to_use: list[str]
    likely_questions: list[str]
    technical_topics: list[str]
    star_examples: list[str]
    questions_to_ask: list[str]
    preparation_tasks: list[str]


@dataclass(frozen=True)
class WeeklyCoachReport:
    headline: str
    diagnosis: str
    wins: list[str]
    risks: list[str]
    next_week_plan: list[str]
    avoid_next_week: list[str]


def normalise_text(*values: str) -> str:
    return " ".join(value or "" for value in values).lower()


def analyze_job_posting(
    company_name: str,
    job_title: str,
    location: str,
    job_posting: str,
) -> JobPostingAnalysis:
    text = normalise_text(company_name, job_title, location, job_posting)
    score = 0
    risks: list[str] = []

    if any(title in text for title in TARGET_TITLES):
        score += 25
    elif any(title in text for title in TARGET_TITLES_AE_STRETCH):
        score += 15
        risks.append("This looks like an AE/DE stretch target; check tool gaps before applying.")
    else:
        risks.append(
            "Role title is not clearly one of the preferred junior data/reporting/BI "
            "targets."
        )

    if any(signal in text for signal in GOOD_LOCATION_WORDS):
        score += 20
    elif "remote" in text:
        score += 14
    else:
        risks.append("Location is not clearly London, Croydon, South London, or Remote UK.")

    if any(level in text for level in ["junior", "graduate", "entry", "trainee", "0-2", "1-2"]):
        score += 20
    elif any(signal in text for signal in SENIOR_SIGNALS):
        risks.append("Seniority may be too high for the current target market.")
    else:
        score += 8
        risks.append("Experience level is unclear; verify before applying.")

    matched_skills = [skill for skill in GOOD_SKILLS if skill in text]
    score += min(25, len(matched_skills) * 4)

    found_deal_breakers = [breaker for breaker in DEAL_BREAKERS if breaker in text]
    found_learning_targets = [target for target in LEARNING_TARGETS if target in text]

    if found_deal_breakers:
        score -= 25
        risks.append("Hard requirement or deal-breaker signals detected.")
    else:
        score += 10

    if found_learning_targets:
        risks.append(
            "Learning-target tools detected: "
            + ", ".join(sorted(set(found_learning_targets)))
            + ". Treat these as gaps to check, not automatic deal-breakers."
        )

    if any(signal in text for signal in SENIOR_SIGNALS):
        score -= 15

    score = max(0, min(100, score))

    if score >= 80:
        recommendation = "Apply — strong match"
        severity = "success"
    elif score >= 60:
        recommendation = "Apply selectively — check gaps first"
        severity = "primary"
    elif score >= 40:
        recommendation = "Review carefully before applying"
        severity = "warning"
    else:
        recommendation = "Skip for now — weak fit"
        severity = "danger"

    recommended_cv = recommend_cv_from_text(text)
    recommended_projects = recommend_projects_from_text(text)

    cover_letter_focus = [
        "Connect your finance/operations background to the role's reporting needs.",
        "Mention one concrete Django/Python analytics project as evidence.",
        "Keep claims evidence-based and avoid overstating tools not proven in your portfolio.",
    ]
    if "sql" in matched_skills:
        cover_letter_focus.append(
            "Make SQL/database evidence visible through models, queries, or reporting "
            "outputs."
        )
    if "excel" in matched_skills:
        cover_letter_focus.append(
            "Mention advanced Excel, reporting discipline, and operational accuracy."
        )

    next_actions = [
        "Save the role in Applications if the fit score is acceptable.",
        f"Use {recommended_cv} as the starting CV version.",
        "Select the strongest matching portfolio project before drafting the cover letter.",
        "Set a follow-up date 7 working days after submission.",
    ]

    explanation = (
        "This analysis is a local rule-based AI-style assessment. It uses role title, "
        "seniority, location, skill keywords, "
        "and deal-breaker signals to produce a practical apply/skip recommendation."
    )

    return JobPostingAnalysis(
        fit_score=score,
        recommendation=recommendation,
        severity=severity,
        matched_skills=matched_skills,
        risks=risks,
        deal_breakers=found_deal_breakers,
        recommended_cv=recommended_cv,
        recommended_projects=recommended_projects,
        cover_letter_focus=cover_letter_focus,
        next_actions=next_actions,
        explanation=explanation,
    )


def recommend_cv_from_text(text: str) -> str:
    """Return the locked CV filename for job-posting and interview-prep analysis."""
    # recommend_cv_from_text() returns the locked CV filename now.
    # A future recommend_cv_angle() helper can recommend Data Analyst / BI /
    # FinTech / AE positioning later.
    # TODO (Sprint 31): restore role-angle logic, e.g. finance/risk -> FinTech,
    # bi/dashboard -> BI, etl/api -> AE, default -> Data Analyst.
    return LOCKED_CV


def recommend_projects_from_text(text: str) -> list[str]:
    if any(word in text for word in ["finance", "risk", "trading", "market", "banking"]):
        return ["TradeIntel 360", "RiskWise Planner", "MarketVista Dashboard"]
    if any(
        word in text
        for word in ["operations", "kpi", "margin", "waste", "product performance"]
    ):
        return ["BakeOps Intelligence", "CareerFunnel Tracker", "MarketVista Dashboard"]
    if any(word in text for word in ["etl", "api", "pipeline", "integration"]):
        return ["DataBridge Market API", "MarketVista Dashboard", "TradeIntel 360"]
    return ["BakeOps Intelligence", "MarketVista Dashboard", "CareerFunnel Tracker"]


def build_next_best_actions(user, limit: int = 8) -> list[AgentAction]:
    today = timezone.localdate()
    actions: list[AgentAction] = []

    due_followups = JobApplication.objects.filter(user=user, follow_up_date__lte=today).exclude(
        follow_up_status__in=[
            FollowUpStatus.SENT,
            FollowUpStatus.RESPONDED,
            FollowUpStatus.NOT_NEEDED,
        ]
    )[:5]
    for app in due_followups:
        actions.append(
            AgentAction(
                priority="High",
                title=f"Follow up with {app.company_name}",
                reason=(
                    f"Follow-up date was {app.follow_up_date} and status is "
                    f"{app.get_follow_up_status_display()}."
                ),
                recommended_action=(
                    "Send a short, polite follow-up and update the follow-up status."
                ),
                related_url=app.get_absolute_url(),
            )
        )

    upcoming_interviews = InterviewPrep.objects.filter(
        user=user,
        interview_date__gte=today,
        interview_date__lte=today + timedelta(days=7),
    ).order_by("interview_date")[:3]
    for interview in upcoming_interviews:
        actions.append(
            AgentAction(
                priority="High",
                title=f"Prepare for {interview.application.company_name} interview",
                reason=(
                    f"Interview is scheduled for {interview.interview_date}; "
                    f"readiness score is {interview.readiness_score}%."
                ),
                recommended_action=(
                    "Complete the interview checklist and prepare one project "
                    "walkthrough."
                ),
                related_url=interview.get_absolute_url(),
            )
        )

    missing_cv = JobApplication.objects.filter(user=user, cv_version="")[:3]
    for app in missing_cv:
        actions.append(
            AgentAction(
                priority="Medium",
                title=f"Add CV version for {app.company_name}",
                reason="CV version is missing, which weakens performance analysis by CV type.",
                recommended_action="Update the application with the CV version used.",
                related_url=app.get_absolute_url(),
            )
        )

    week_start = today - timedelta(days=today.weekday())
    weekly_apps = JobApplication.objects.filter(user=user, date_applied__gte=week_start).count()
    if weekly_apps < 10:
        actions.append(
            AgentAction(
                priority="Medium",
                title="Increase application volume this week",
                reason=f"Only {weekly_apps} applications are logged this week.",
                recommended_action=(
                    "Apply to suitable junior Data Analyst, Reporting Analyst, BI "
                    "Analyst, or Finance Data Analyst roles."
                ),
            )
        )

    metrics = build_funnel_metrics(user)
    diagnosis = diagnose_funnel(metrics)
    actions.append(
        AgentAction(
            priority="Strategic",
            title=diagnosis.diagnosis_title,
            reason=diagnosis.explanation,
            recommended_action=diagnosis.recommended_action,
        )
    )

    return actions[:limit]


def generate_followup_message(application: JobApplication) -> FollowUpDraft:
    contact = application.contact_name or "Hiring Team"
    subject = f"Follow-up on {application.job_title} application"
    body = (
        f"Dear {contact},\n\n"
        f"I hope you are well. I wanted to follow up on my application for the "
        f"{application.job_title} role at {application.company_name}, "
        f"submitted on {application.date_applied}.\n\n"
        "I remain very interested in the opportunity because it aligns with my "
        "experience in reporting, KPI analysis, "
        "Python/Django analytics projects, and business-facing data work.\n\n"
        "Please let me know if there is any further information I can provide.\n\n"
        "Kind regards,\n"
        "Aminul Islam"
    )
    reason = (
        "Generated because the application is ready for a polite status check without "
        "sounding pushy."
    )
    return FollowUpDraft(subject=subject, body=body, reason=reason)


def generate_interview_prep(application: JobApplication) -> InterviewPrepPack:
    text = normalise_text(
        application.job_title,
        application.required_skills,
        application.job_description,
        application.notes,
    )
    projects = recommend_projects_from_text(text)
    cv = recommend_cv_from_text(text)
    profile_angle = (
        "Position yourself as a finance/operations professional moving into analytics, "
        f"using {cv} and evidence from "
        f"{projects[0]} to show practical KPI, reporting, and decision-support capability."
    )
    likely_questions = [
        "Tell me about yourself and your move into data analytics.",
        (
            f"Why are you interested in the {application.job_title} role at "
            f"{application.company_name}?"
        ),
        "Walk me through one analytics project from problem to business output.",
        "How do you handle messy or incomplete data?",
        "How have you used Excel, Python, SQL, or dashboards in practical work?",
        "What would you do if a stakeholder challenged your analysis?",
    ]
    technical_topics = [
        "Excel lookups/pivots",
        "SQL filtering and joins",
        "Python/pandas data cleaning",
        "KPI definitions",
        "Dashboard interpretation",
    ]
    if "power bi" in text:
        technical_topics.append("Power BI dashboard concepts")
    if "api" in text or "etl" in text:
        technical_topics.extend(["API ingestion", "ETL workflow explanation"])
    star_examples = [
        "A time you improved or organised a reporting process.",
        "A time you handled accuracy under pressure in finance/operations work.",
        "A time you learned a technical skill and applied it in a project.",
        "A time you explained something complex to a non-technical person.",
    ]
    questions_to_ask = [
        "What are the most important reports or metrics this role owns?",
        "What tools does the team use for analysis and reporting?",
        "What would success look like in the first three months?",
        "How does the team handle data quality or unclear requirements?",
    ]
    preparation_tasks = [
        "Prepare a 60-second profile answer.",
        f"Prepare a 2-minute walkthrough of {projects[0]}.",
        "Prepare one STAR example from finance/operations work.",
        "Review SQL basics and one Python/pandas example.",
        "Write three questions to ask the interviewer.",
    ]
    return InterviewPrepPack(
        profile_angle=profile_angle,
        projects_to_use=projects,
        likely_questions=likely_questions,
        technical_topics=technical_topics,
        star_examples=star_examples,
        questions_to_ask=questions_to_ask,
        preparation_tasks=preparation_tasks,
    )


def build_weekly_coach_report(user) -> WeeklyCoachReport:
    metrics = build_funnel_metrics(user)
    diagnosis = diagnose_funnel(metrics)
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())
    logs = DailyLog.objects.filter(user=user, log_date__gte=week_start)
    weekly_reviews = WeeklyReview.objects.filter(user=user)

    actual = sum(log.actual_applications for log in logs)
    target = sum(log.target_applications for log in logs)
    hit_days = sum(1 for log in logs if log.target_met)

    wins: list[str] = []
    risks: list[str] = []

    if metrics.response_rate >= 15:
        wins.append(
            f"Response rate is {metrics.response_rate}%, which suggests some "
            "targeting is working."
        )
    if metrics.interview_rate > 0:
        wins.append(
            "The funnel has reached interview stage, so CV/screening evidence is not "
            "completely failing."
        )
    if hit_days > 0:
        wins.append(f"You hit the daily target on {hit_days} logged day(s) this week.")

    if target and actual < target:
        risks.append(f"Application volume is below target: {actual}/{target} this week.")
    if metrics.response_rate < 10 and metrics.total_applications >= 10:
        risks.append("Response rate is still weak; CV positioning or role targeting needs review.")
    if JobApplication.objects.filter(user=user, follow_up_date__lte=today).exclude(
        follow_up_status__in=[
            FollowUpStatus.SENT,
            FollowUpStatus.RESPONDED,
            FollowUpStatus.NOT_NEEDED,
        ]
    ).exists():
        risks.append("There are overdue follow-ups that may be costing momentum.")

    if not wins:
        wins.append(
            "The main win is that the platform now has data to diagnose rather than "
            "guessing."
        )
    if not risks:
        risks.append("No major weekly risk is obvious yet; keep logging consistently.")

    next_week_plan = [
        "Set a realistic weekly application target and protect time for submissions.",
        "Prioritise junior Data Analyst, Reporting Analyst, BI Analyst, and Finance "
        "Data Analyst roles.",
        "Use the AI Job Posting Analyzer before applying to reduce weak-fit applications.",
        "Prepare interview evidence around projects, not only technical tools.",
    ]
    avoid_next_week = [
        "Avoid senior roles with hard 3+ or 5+ year requirements unless the fit is "
        "unusually strong.",
        "Avoid applying without recording CV version and follow-up date.",
        "Avoid spending the whole session browsing without submitting.",
    ]

    if weekly_reviews.exists():
        headline = "AI Weekly Coach — review your pattern and protect next week’s focus"
    else:
        headline = "AI Weekly Coach — start with consistent logging and application volume"

    return WeeklyCoachReport(
        headline=headline,
        diagnosis=diagnosis.diagnosis_title,
        wins=wins,
        risks=risks,
        next_week_plan=next_week_plan,
        avoid_next_week=avoid_next_week,
    )


def get_latest_weekly_review(user):
    """Return the most recent saved weekly review for display context. Read-only."""
    return WeeklyReview.objects.filter(user=user).order_by("-week_ending").first()


def count_weekly_reviews(user) -> int:
    """Count saved weekly reviews for the user. Read-only."""
    return WeeklyReview.objects.filter(user=user).count()


# --- Advanced Smart AI Assistance Layer ---


@dataclass(frozen=True)
class CVGapAnalysis:
    score: int
    matched_skills: list[str]
    partial_matches: list[str]
    missing_skills: list[str]
    evidence_to_emphasise: list[str]
    keywords_to_add_honestly: list[str]
    claims_to_avoid: list[str]
    recommendation: str


@dataclass(frozen=True)
class CoverLetterQualityResult:
    score: int
    quality_label: str
    strengths: list[str]
    weaknesses: list[str]
    recommended_fixes: list[str]
    evidence_warning: str


@dataclass(frozen=True)
class RejectionPatternReport:
    total_rejections: int
    headline: str
    patterns: list[str]
    likely_causes: list[str]
    recommendations: list[str]
    highest_risk_cv_versions: list[str]
    highest_risk_sources: list[str]
    highest_risk_role_terms: list[str]


@dataclass(frozen=True)
class CVVersionPerformanceRow:
    cv_version: str
    applications: int
    responses: int
    interviews: int
    offers: int
    rejections: int
    response_rate: float
    interview_rate: float
    offer_rate: float
    recommendation: str


@dataclass(frozen=True)
class SmartNotification:
    priority: str
    title: str
    message: str
    recommended_action: str
    related_url: str | None = None


REQUIRED_SKILLS = [
    "python",
    "sql",
    "excel",
    "power bi",
    "tableau",
    "dashboard",
    "reporting",
    "kpi",
    "pandas",
    "etl",
    "api",
    "data quality",
    "stakeholder",
    "finance",
    "reconciliation",
    "analytics",
    "data modelling",
    "visualisation",
    "statistics",
    "snowflake",
    "dbt",
    "aws",
]

USER_EVIDENCE_MAP = {
    "python": "Python portfolio projects and data-processing workflows",
    "django": (
        "Django-based analytics platforms including BakeOps, MarketVista, RiskWise, "
        "and CareerFunnel"
    ),
    "excel": "Advanced Excel, cashflow platform, scorecards, formulas, and reporting experience",
    "reporting": (
        "Operational reporting, KPI tracking, and monthly performance reporting "
        "experience"
    ),
    "dashboard": "MarketVista, BakeOps, and CareerFunnel dashboard pages",
    "kpi": "KPI modelling in BakeOps Intelligence and operational reporting roles",
    "finance": (
        "Money transfer, FX, remittance, reconciliations, and finance operations "
        "background"
    ),
    "reconciliation": "FX/remittance operations and audit-ready cashflow records",
    "pandas": "Python/pandas analytics project work",
    "etl": "DataBridge Market API and analytics ETL-style workflows",
    "api": "Django API-style JSON endpoints and market-data ingestion projects",
    "stakeholder": "Agent training, operational support, and business-facing reporting experience",
    "sql": (
        "Database-backed Django projects and dashboard-ready data models; strengthen "
        "explicit SQL examples if needed"
    ),
}

HARD_GAP_TERMS = [
    "dbt",
    "snowflake",
    "airflow",
    "spark",
    "kafka",
    "aws redshift",
    "sc clearance",
    "dv clearance",
]


def extract_skill_terms(text: str) -> list[str]:
    normalized = text.lower()
    found = []
    for skill in REQUIRED_SKILLS:
        if skill in normalized:
            found.append(skill)
    return sorted(set(found))


def analyze_cv_gap(job_description: str, cv_evidence: str = "") -> CVGapAnalysis:
    job_text = job_description.lower()
    evidence_text = cv_evidence.lower()
    job_skills = extract_skill_terms(job_text)

    matched: list[str] = []
    partial: list[str] = []
    missing: list[str] = []
    evidence_to_emphasise: list[str] = []

    for skill in job_skills:
        if skill in evidence_text or skill in USER_EVIDENCE_MAP:
            if (
                skill in ["sql", "power bi", "tableau", "dbt", "snowflake", "aws"]
                and skill not in evidence_text
            ):
                partial.append(skill)
            else:
                matched.append(skill)
            if skill in USER_EVIDENCE_MAP:
                evidence_to_emphasise.append(USER_EVIDENCE_MAP[skill])
        else:
            missing.append(skill)

    hard_gaps = [term for term in HARD_GAP_TERMS if term in job_text and term not in evidence_text]
    for term in hard_gaps:
        if term not in missing:
            missing.append(term)

    total = max(len(job_skills), 1)
    score = round(((len(matched) * 1.0) + (len(partial) * 0.5)) / total * 100)
    if hard_gaps:
        score = max(0, score - 20)

    keywords_to_add = [skill for skill in matched + partial if skill not in evidence_text][:8]
    claims_to_avoid = [
        f"Do not claim production-level experience with {term} unless you can prove it."
        for term in hard_gaps
    ]
    if "senior" in job_text or "5+ years" in job_text or "3+ years" in job_text:
        claims_to_avoid.append(
            "Do not position this as a junior-friendly role without checking the "
            "seniority requirement."
        )

    if score >= 75:
        recommendation = "Strong enough to apply if seniority and location also fit."
    elif score >= 55:
        recommendation = (
            "Apply selectively; tailor the CV around the strongest evidence and "
            "acknowledge weaker tools carefully."
        )
    else:
        recommendation = "Weak fit; skip unless the missing skills are clearly optional."

    return CVGapAnalysis(
        score=score,
        matched_skills=matched,
        partial_matches=partial,
        missing_skills=sorted(set(missing)),
        evidence_to_emphasise=list(dict.fromkeys(evidence_to_emphasise))[:8],
        keywords_to_add_honestly=keywords_to_add,
        claims_to_avoid=claims_to_avoid
        or [
            "Avoid exaggerating tool depth; keep evidence project-based and realistic."
        ],
        recommendation=recommendation,
    )


@dataclass(frozen=True)
class CVTailoringAdvisorResult:
    recommended_cv: str
    cv_angle: str
    role_family: str
    strongest_experience: list[str]
    strongest_projects: list[str]
    matched_skills: list[str]
    partial_matches: list[str]
    missing_skills: list[str]
    risks: list[str]
    deal_breakers: list[str]
    cover_letter_angle: list[str]
    interview_evidence_points: list[str]
    claim_safety_notes: list[str]
    approval_reminder: str


APPROVAL_REMINDER = (
    "Review and approve all suggested wording before adding it to a CV, cover letter, "
    "recruiter message, or application."
)

CLAIM_SAFETY_NOTES = [
    "Suggestions are advisory only.",
    "No final CV is generated.",
    "No cover letter is finalized.",
    "No application is submitted.",
    "No Gmail, Calendar, scraping, external AI, or recruiter automation is used.",
    "User must manually approve wording before using it externally.",
]

FINANCE_EXPERIENCE_ANGLES = [
    "FX, remittance, finance operations, and reconciliation discipline",
    "Operational reporting and KPI tracking",
    "Stakeholder-facing reporting and training",
]

BI_EXPERIENCE_ANGLES = [
    "Operational reporting and KPI tracking",
    "Dashboard-ready data modelling",
    "Python/Django analytics project delivery",
    "Stakeholder-facing reporting and training",
]

AE_EXPERIENCE_ANGLES = [
    "Python/Django analytics project delivery",
    "Dashboard-ready data modelling",
    "Pipeline/API-style portfolio evidence with honest tool-gap boundaries",
]

GENERAL_DA_EXPERIENCE_ANGLES = [
    "Python/Django analytics project delivery",
    "Operational reporting and KPI tracking",
    "Dashboard-ready data modelling",
    "Stakeholder-facing reporting and training",
]

REVIEW_EXPERIENCE_ANGLES = [
    "Verify seniority, location, and hard requirements before emphasizing any angle",
    "Keep claims tied to documented portfolio and operations background only",
]


def _detect_cv_angle_and_role_family(
    text: str,
    job_analysis: JobPostingAnalysis,
) -> tuple[str, str]:
    if (
        job_analysis.deal_breakers
        or job_analysis.fit_score < 40
        or "Skip" in job_analysis.recommendation
    ):
        return (
            "Review-first — verify seniority, deal-breakers, and tool gaps before tailoring",
            "Review Carefully",
        )

    finance_signals = [
        "finance",
        "fintech",
        "risk",
        "banking",
        "trading",
        "remittance",
        "reconciliation",
        "fx",
    ]
    bi_signals = [
        "bi analyst",
        "business intelligence",
        "power bi",
        "tableau",
        "dashboard",
        "reporting analyst",
        "insights analyst",
    ]
    ae_signals = [
        "etl",
        "api",
        "pipeline",
        "integration",
        "analytics engineer",
        "data engineer",
        "data product",
    ]

    if any(title in text for title in TARGET_TITLES_AE_STRETCH) or any(
        signal in text for signal in ae_signals
    ):
        return (
            "Analytics Engineering / Data Product stretch — emphasize pipeline/API "
            "evidence and honest tool-gap boundaries",
            "Analytics Engineering / Data Product Stretch",
        )
    if any(signal in text for signal in finance_signals):
        return (
            "Finance / FinTech / Risk — emphasize reconciliation discipline, "
            "operational reporting, and governed analytics",
            "Finance / FinTech Analytics",
        )
    if any(signal in text for signal in bi_signals):
        return (
            "BI / Reporting / Dashboard — emphasize KPI reporting, dashboards, "
            "and stakeholder-ready outputs",
            "BI / Reporting Analytics",
        )
    if any(title in text for title in TARGET_TITLES):
        return (
            "General Data Analyst — emphasize Python/Django analytics delivery "
            "and evidence-based reporting",
            "Data Analyst",
        )

    return (
        "Review-first — role signals are unclear; confirm fit before tailoring",
        "Review Carefully",
    )


def _experience_angles_for_role_family(role_family: str) -> list[str]:
    if role_family == "Finance / FinTech Analytics":
        return list(FINANCE_EXPERIENCE_ANGLES)
    if role_family == "BI / Reporting Analytics":
        return list(BI_EXPERIENCE_ANGLES)
    if role_family == "Analytics Engineering / Data Product Stretch":
        return list(AE_EXPERIENCE_ANGLES)
    if role_family == "Data Analyst":
        return list(GENERAL_DA_EXPERIENCE_ANGLES)
    return list(REVIEW_EXPERIENCE_ANGLES)


def _build_tailoring_risks(
    text: str,
    location: str,
    job_analysis: JobPostingAnalysis,
    cv_gap: CVGapAnalysis,
) -> list[str]:
    risks: list[str] = list(job_analysis.risks)

    if any(signal in text for signal in SENIOR_SIGNALS):
        if "Seniority" not in " ".join(risks):
            risks.append("Seniority risk — role may be above current target market.")

    location_text = normalise_text(location)
    if location_text and not any(
        loc in location_text for loc in GOOD_LOCATION_WORDS
    ) and "remote" not in location_text:
        risks.append(
            "Location risk — location is not clearly London, Croydon, South London, "
            "or Remote UK."
        )

    hard_gaps = [term for term in HARD_GAP_TERMS if term in text]
    if hard_gaps:
        risks.append(
            "Hard-tool gap risk — "
            + ", ".join(sorted(set(hard_gaps)))
            + "; treat as learning gaps unless clearly optional."
        )

    learning_hits = [target for target in LEARNING_TARGETS if target in text]
    if learning_hits and not hard_gaps:
        risks.append(
            "Learning-target tools detected: "
            + ", ".join(sorted(set(learning_hits)))
            + "; do not claim production depth without evidence."
        )

    if not any(title in text for title in TARGET_TITLES) and not any(
        title in text for title in TARGET_TITLES_AE_STRETCH
    ):
        risks.append("Unclear role-fit risk — title is not a clear junior analytics target.")

    if cv_gap.claims_to_avoid:
        for claim in cv_gap.claims_to_avoid[:2]:
            if claim not in risks:
                risks.append(f"Overclaim risk — {claim}")

    return list(dict.fromkeys(risks))


def _build_cover_letter_angles(
    role_family: str,
    cv_gap: CVGapAnalysis,
    job_analysis: JobPostingAnalysis,
) -> list[str]:
    angles = [
        "Connect finance/operations background to the role's reporting needs where truthful.",
        "Cite one relevant portfolio project with problem → approach → business output.",
        "Keep unsupported tools as learning gaps or partial exposure, not proven expertise.",
        "Avoid exaggerated claims; align wording with repository evidence only.",
    ]
    if role_family == "Finance / FinTech Analytics":
        angles.append(
            "Highlight reconciliation discipline and operational KPI accuracy from "
            "finance/operations work."
        )
    elif role_family == "BI / Reporting Analytics":
        angles.append(
            "Lead with dashboard/KPI storytelling and stakeholder-ready reporting examples."
        )
    elif role_family == "Analytics Engineering / Data Product Stretch":
        angles.append(
            "Frame pipeline/API projects honestly and acknowledge optional cloud/dbt "
            "requirements as stretch goals."
        )
    if cv_gap.partial_matches:
        angles.append(
            "Mention partial tool exposure only where portfolio evidence supports it: "
            + ", ".join(cv_gap.partial_matches[:4])
            + "."
        )
    angles.extend(job_analysis.cover_letter_focus[:2])
    return list(dict.fromkeys(angles))[:8]


def _build_interview_evidence_points(role_family: str, strongest_projects: list[str]) -> list[str]:
    points = [
        "Explain one portfolio project from problem to business output.",
        "Explain how KPI/reporting logic was designed and validated.",
        "Explain data quality checks and manual approval boundaries in CareerFunnel Tracker.",
    ]
    if role_family == "Finance / FinTech Analytics":
        points.append(
            "Explain finance/reconciliation discipline and how it supports accurate reporting."
        )
    if strongest_projects:
        points.append(
            f"Prepare a concise walkthrough of {strongest_projects[0]} aligned to the role."
        )
    return list(dict.fromkeys(points))[:6]


def _build_rule_based_cv_tailoring_advisor(
    company_name: str = "",
    job_title: str = "",
    location: str = "",
    job_description: str = "",
    cv_evidence: str = "",
) -> CVTailoringAdvisorResult:
    """Rule-based CV tailoring baseline; advisory only — no document generation."""
    combined_description = " ".join(
        part for part in (job_title, job_description) if part
    ).strip()
    text = normalise_text(company_name, job_title, location, job_description, cv_evidence)

    job_analysis = analyze_job_posting(
        company_name=company_name,
        job_title=job_title,
        location=location,
        job_posting=job_description,
    )
    cv_gap = analyze_cv_gap(combined_description, cv_evidence)

    cv_angle, role_family = _detect_cv_angle_and_role_family(text, job_analysis)
    strongest_projects = recommend_projects_from_text(text)
    strongest_experience = _experience_angles_for_role_family(role_family)
    risks = _build_tailoring_risks(text, location, job_analysis, cv_gap)

    deal_breakers = sorted(set(job_analysis.deal_breakers))
    if any(signal in text for signal in SENIOR_SIGNALS) and not any(
        level in text for level in ["junior", "graduate", "entry", "trainee", "0-2", "1-2"]
    ):
        if "seniority mismatch" not in " ".join(deal_breakers).lower():
            risks.append(
                "Seniority signal detected — treat as a blocker unless requirements are flexible."
            )

    cover_letter_angle = _build_cover_letter_angles(role_family, cv_gap, job_analysis)
    interview_evidence_points = _build_interview_evidence_points(
        role_family, strongest_projects
    )

    return CVTailoringAdvisorResult(
        recommended_cv=LOCKED_CV,
        cv_angle=cv_angle,
        role_family=role_family,
        strongest_experience=strongest_experience,
        strongest_projects=strongest_projects,
        matched_skills=cv_gap.matched_skills,
        partial_matches=cv_gap.partial_matches,
        missing_skills=cv_gap.missing_skills,
        risks=risks,
        deal_breakers=deal_breakers,
        cover_letter_angle=cover_letter_angle,
        interview_evidence_points=interview_evidence_points,
        claim_safety_notes=list(CLAIM_SAFETY_NOTES),
        approval_reminder=APPROVAL_REMINDER,
    )


# --- Sprint 34B: CV tailoring semantic contract ---

CV_TAILORING_SEMANTIC_REQUIRED_FIELDS = [
    "semantic_matched_skills",
    "semantic_partial_matches",
    "semantic_gaps",
    "semantic_project_highlights",
    "semantic_experience_angles",
    "semantic_risks",
    "semantic_cover_letter_themes",
    "semantic_interview_points",
    "reasoning_summary",
    "claim_safety_notes",
    "manual_review_required",
]

CV_TAILORING_FORBIDDEN_FIELDS = [
    "full_cv_text",
    "professional_summary",
    "experience_bullets",
    "cover_letter_body",
    "cover_letter_text",
    "cv_body",
    "application_letter",
    "recruiter_message",
    "linkedin_post",
    "recommended_cv",
]

CV_TAILORING_CLAIM_SAFETY_NOTES = [
    "CV tailoring semantic output is advisory only.",
    "Manual review is required before using recommendations externally.",
    "No final CV is generated.",
    "No cover letter body is generated.",
    "No application is submitted.",
    "No auto-apply or auto-save is used.",
    (
        "No Gmail, Calendar, scraping, recruiter automation, or OAuth "
        "integration is used."
    ),
    "Do not invent skills, employers, dates, metrics, or experience.",
    "Gap-tier and learning-target skills must not be claimed as proven expertise.",
]

CV_TAILORING_SEMANTIC_LIST_FIELDS = [
    "semantic_matched_skills",
    "semantic_partial_matches",
    "semantic_gaps",
    "semantic_project_highlights",
    "semantic_experience_angles",
    "semantic_risks",
    "semantic_cover_letter_themes",
    "semantic_interview_points",
    "claim_safety_notes",
]


@dataclass(frozen=True)
class CVTailoringSemanticResult:
    semantic_matched_skills: list[str]
    semantic_partial_matches: list[str]
    semantic_gaps: list[str]
    semantic_project_highlights: list[str]
    semantic_experience_angles: list[str]
    semantic_risks: list[str]
    semantic_cover_letter_themes: list[str]
    semantic_interview_points: list[str]
    reasoning_summary: str
    claim_safety_notes: list[str]
    manual_review_required: bool


def _merge_cv_tailoring_claim_notes(extra: list[str]) -> list[str]:
    merged = list(CV_TAILORING_CLAIM_SAFETY_NOTES)
    for note in extra:
        if note and note not in merged:
            merged.append(note)
    return merged


def parse_cv_tailoring_semantic_payload(payload: dict) -> CVTailoringSemanticResult:
    """Validate Claude CV tailoring semantic JSON. No network or DB writes."""
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary.")

    errors: list[str] = []
    for field in CV_TAILORING_FORBIDDEN_FIELDS:
        if field in payload:
            errors.append(f"Forbidden field present: {field}.")

    for field in CV_TAILORING_SEMANTIC_REQUIRED_FIELDS:
        if field not in payload:
            errors.append(f"Missing required field: {field}.")

    manual_review = payload.get("manual_review_required")
    if manual_review is not True:
        errors.append("manual_review_required must be true.")

    raw_summary = payload.get("reasoning_summary")
    if not isinstance(raw_summary, str):
        errors.append("reasoning_summary must be a string.")
    elif not raw_summary.strip():
        errors.append("reasoning_summary must be a non-empty string.")

    list_fields: dict[str, list[str]] = {}
    for field in CV_TAILORING_SEMANTIC_LIST_FIELDS:
        try:
            list_fields[field] = _parse_string_list_field(payload.get(field), field)
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise ValueError("; ".join(errors))

    return CVTailoringSemanticResult(
        semantic_matched_skills=list_fields["semantic_matched_skills"],
        semantic_partial_matches=list_fields["semantic_partial_matches"],
        semantic_gaps=list_fields["semantic_gaps"],
        semantic_project_highlights=list_fields["semantic_project_highlights"],
        semantic_experience_angles=list_fields["semantic_experience_angles"],
        semantic_risks=list_fields["semantic_risks"],
        semantic_cover_letter_themes=list_fields["semantic_cover_letter_themes"],
        semantic_interview_points=list_fields["semantic_interview_points"],
        reasoning_summary=str(payload["reasoning_summary"]).strip(),
        claim_safety_notes=_merge_cv_tailoring_claim_notes(
            list_fields["claim_safety_notes"]
        ),
        manual_review_required=True,
    )


CV_TAILORING_SEMANTIC_SUCCESS_NOTE = (
    "Claude semantic enhancement is advisory only. Manual review required."
)
CV_TAILORING_SEMANTIC_FALLBACK_NOTE = (
    "Semantic enhancement unavailable; rule-based fallback used."
)


def _merge_unique_string_lists(
    *groups: list[str],
    limit: int | None = None,
) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            text = item.strip()
            if not text:
                continue
            key = text.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(text)
    if limit is not None:
        return merged[:limit]
    return merged


def _filter_safe_advisory_lines(lines: list[str]) -> list[str]:
    from .evidence_bank import contains_forbidden_claim_field

    return [
        line.strip()
        for line in lines
        if line.strip() and not contains_forbidden_claim_field(line)
    ]


def _with_cv_tailoring_fallback_note(
    rule_based_result: CVTailoringAdvisorResult,
    detail: str = "",
) -> CVTailoringAdvisorResult:
    notes = list(rule_based_result.claim_safety_notes)
    fallback_note = CV_TAILORING_SEMANTIC_FALLBACK_NOTE
    if detail and detail not in notes:
        notes.append(detail)
    if fallback_note not in notes:
        notes.append(fallback_note)
    return CVTailoringAdvisorResult(
        recommended_cv=rule_based_result.recommended_cv,
        cv_angle=rule_based_result.cv_angle,
        role_family=rule_based_result.role_family,
        strongest_experience=list(rule_based_result.strongest_experience),
        strongest_projects=list(rule_based_result.strongest_projects),
        matched_skills=list(rule_based_result.matched_skills),
        partial_matches=list(rule_based_result.partial_matches),
        missing_skills=list(rule_based_result.missing_skills),
        risks=list(rule_based_result.risks),
        deal_breakers=list(rule_based_result.deal_breakers),
        cover_letter_angle=list(rule_based_result.cover_letter_angle),
        interview_evidence_points=list(rule_based_result.interview_evidence_points),
        claim_safety_notes=notes,
        approval_reminder=rule_based_result.approval_reminder,
    )


def _build_evidence_catalog_for_prompt() -> dict:
    from .evidence_bank import EVIDENCE_ENTRIES, PROJECT_ENTRIES

    def _skill_rows(tier: str) -> list[dict[str, str]]:
        return [
            {
                "id": entry.skill_id,
                "name": entry.display_name,
                "summary": entry.evidence_summary,
            }
            for entry in EVIDENCE_ENTRIES.values()
            if entry.tier == tier
        ]

    return {
        "strong_skills": _skill_rows("strong"),
        "partial_skills": _skill_rows("partial"),
        "gap_learning_skills": _skill_rows("gap_learning"),
        "projects": [
            {
                "id": entry.project_id,
                "name": entry.display_name,
                "summary": entry.evidence_summary,
            }
            for entry in PROJECT_ENTRIES.values()
        ],
    }


def build_cv_tailoring_semantic_prompt(
    company_name: str,
    job_title: str,
    location: str,
    job_description: str,
    cv_evidence: str,
    rule_based_result: CVTailoringAdvisorResult,
) -> dict:
    """Build provider prompt dict from rule-based baseline and evidence bank catalog."""
    return {
        "company_name": company_name,
        "job_title": job_title,
        "location": location,
        "job_description": job_description,
        "cv_evidence": cv_evidence,
        "rule_based": {
            "cv_angle": rule_based_result.cv_angle,
            "role_family": rule_based_result.role_family,
            "matched_skills": list(rule_based_result.matched_skills),
            "partial_matches": list(rule_based_result.partial_matches),
            "missing_skills": list(rule_based_result.missing_skills),
            "strongest_projects": list(rule_based_result.strongest_projects),
            "strongest_experience": list(rule_based_result.strongest_experience),
            "risks": list(rule_based_result.risks),
            "deal_breakers": list(rule_based_result.deal_breakers),
            "cover_letter_angle": list(rule_based_result.cover_letter_angle),
            "interview_evidence_points": list(
                rule_based_result.interview_evidence_points
            ),
        },
        "evidence_catalog": _build_evidence_catalog_for_prompt(),
        "required_output_schema": {
            "fields": list(CV_TAILORING_SEMANTIC_REQUIRED_FIELDS),
            "forbidden_fields": list(CV_TAILORING_FORBIDDEN_FIELDS),
        },
        "safety_rules": [
            "Output is advisory only.",
            "Manual review is required before using recommendations externally.",
            "Do not generate a final CV, cover letter body, or application copy.",
            "Do not claim auto-apply, auto-save, or application submission.",
            "Do not invent skills, employers, dates, metrics, or experience.",
            "Do not include Gmail, Calendar, inbox, OAuth, or contact data.",
            "Gap-tier skills must appear in semantic_gaps only, never as proven matches.",
        ],
    }


def merge_cv_tailoring_with_semantic(
    rule_based_result: CVTailoringAdvisorResult,
    semantic_result: CVTailoringSemanticResult,
) -> CVTailoringAdvisorResult:
    """Merge validated semantic findings into the rule-based advisor result."""
    from .evidence_bank import (
        filter_claimable_for_matched,
        filter_gap_learning_skills,
        filter_partial_skills,
        validate_project_names,
    )

    semantic_skill_attempts = (
        semantic_result.semantic_matched_skills + semantic_result.semantic_partial_matches
    )
    gap_demoted = filter_gap_learning_skills(semantic_skill_attempts)

    matched_skills = _merge_unique_string_lists(
        rule_based_result.matched_skills,
        filter_claimable_for_matched(semantic_result.semantic_matched_skills),
    )
    partial_matches = _merge_unique_string_lists(
        rule_based_result.partial_matches,
        filter_partial_skills(
            semantic_result.semantic_partial_matches
            + semantic_result.semantic_matched_skills
        ),
    )
    missing_skills = _merge_unique_string_lists(
        rule_based_result.missing_skills,
        semantic_result.semantic_gaps,
        gap_demoted,
    )

    strongest_projects = _merge_unique_string_lists(
        rule_based_result.strongest_projects,
        validate_project_names(semantic_result.semantic_project_highlights),
        limit=6,
    )
    strongest_experience = _merge_unique_string_lists(
        rule_based_result.strongest_experience,
        _filter_safe_advisory_lines(semantic_result.semantic_experience_angles),
        limit=6,
    )
    risks = _merge_unique_string_lists(
        rule_based_result.risks,
        _filter_safe_advisory_lines(semantic_result.semantic_risks),
        limit=10,
    )
    cover_letter_angle = _merge_unique_string_lists(
        rule_based_result.cover_letter_angle,
        _filter_safe_advisory_lines(semantic_result.semantic_cover_letter_themes),
        limit=8,
    )
    interview_evidence_points = _merge_unique_string_lists(
        rule_based_result.interview_evidence_points,
        _filter_safe_advisory_lines(semantic_result.semantic_interview_points),
        limit=6,
    )

    claim_safety_notes = _merge_unique_string_lists(
        rule_based_result.claim_safety_notes,
        semantic_result.claim_safety_notes,
        [CV_TAILORING_SEMANTIC_SUCCESS_NOTE],
    )

    return CVTailoringAdvisorResult(
        recommended_cv=LOCKED_CV,
        cv_angle=rule_based_result.cv_angle,
        role_family=rule_based_result.role_family,
        strongest_experience=strongest_experience,
        strongest_projects=strongest_projects,
        matched_skills=matched_skills,
        partial_matches=partial_matches,
        missing_skills=missing_skills,
        risks=risks,
        deal_breakers=list(rule_based_result.deal_breakers),
        cover_letter_angle=cover_letter_angle,
        interview_evidence_points=interview_evidence_points,
        claim_safety_notes=claim_safety_notes,
        approval_reminder=APPROVAL_REMINDER,
    )


def build_cv_tailoring_advisor(
    company_name: str = "",
    job_title: str = "",
    location: str = "",
    job_description: str = "",
    cv_evidence: str = "",
    provider_callable: Callable[[dict], dict] | None = None,
) -> CVTailoringAdvisorResult:
    """CV tailoring suggestions; rule-based baseline with optional semantic enhancement."""
    rule_based_result = _build_rule_based_cv_tailoring_advisor(
        company_name=company_name,
        job_title=job_title,
        location=location,
        job_description=job_description,
        cv_evidence=cv_evidence,
    )
    if provider_callable is None:
        return rule_based_result

    try:
        prompt = build_cv_tailoring_semantic_prompt(
            company_name=company_name,
            job_title=job_title,
            location=location,
            job_description=job_description,
            cv_evidence=cv_evidence,
            rule_based_result=rule_based_result,
        )
        provider_response = provider_callable(prompt)
        if not isinstance(provider_response, dict):
            return _with_cv_tailoring_fallback_note(
                rule_based_result,
                "Provider callable must return a dictionary payload.",
            )
        semantic_result = parse_cv_tailoring_semantic_payload(provider_response)
    except ValueError as exc:
        return _with_cv_tailoring_fallback_note(
            rule_based_result,
            f"Semantic payload validation failed: {exc}",
        )
    except Exception as exc:
        return _with_cv_tailoring_fallback_note(
            rule_based_result,
            f"Provider callable failed: {exc}",
        )

    return merge_cv_tailoring_with_semantic(rule_based_result, semantic_result)


# --- Sprint 32B: AI fit scoring contract (local/mocked only; no external API) ---

AI_CONFIDENCE_LEVELS = {"low", "medium", "high"}
AI_SCORE_DISAGREEMENT_THRESHOLD = 15

AI_SCORING_CLAIM_SAFETY_NOTES = [
    "AI scoring is advisory only.",
    "Rule-based score remains visible.",
    (
        "Manual review is required before saving or using recommendations "
        "externally."
    ),
    "No application is submitted.",
    "No CV or cover letter is finalized.",
    (
        "No Gmail, Calendar, scraping, recruiter automation, or auto-apply "
        "is used."
    ),
    "Sprint 32B does not call OpenAI or any external AI service.",
]

AI_SCORING_REQUIRED_PAYLOAD_FIELDS = [
    "ai_fit_score",
    "ai_fit_label",
    "confidence",
    "evidence_matches",
    "gaps",
    "deal_breakers",
    "reasoning_summary",
    "recommended_cv_angle",
    "recommended_projects",
    "claim_safety_notes",
]


@dataclass(frozen=True)
class AIFitScoringResult:
    ai_fit_score: int
    ai_fit_label: str
    confidence: str
    evidence_matches: list[str]
    gaps: list[str]
    deal_breakers: list[str]
    reasoning_summary: str
    recommended_cv_angle: str
    recommended_projects: list[str]
    manual_review_required: bool
    claim_safety_notes: list[str]


@dataclass(frozen=True)
class AIFitScoreComparison:
    rule_based_score: int
    ai_fit_score: int
    score_delta: int
    disagreement_flag: bool
    disagreement_summary: str
    manual_review_required: bool
    claim_safety_notes: list[str]


def _merge_ai_scoring_claim_notes(extra: list[str]) -> list[str]:
    merged = list(AI_SCORING_CLAIM_SAFETY_NOTES)
    for note in extra:
        if note and note not in merged:
            merged.append(note)
    return merged


def _validate_fit_score_value(score: object, field_name: str) -> int:
    if isinstance(score, bool) or not isinstance(score, int):
        raise ValueError(f"{field_name} must be an integer between 0 and 100.")
    if score < 0 or score > 100:
        raise ValueError(f"{field_name} must be an integer between 0 and 100.")
    return score


def _parse_string_list_field(value: object, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings.")
    cleaned: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} must be a list of strings.")
        text = item.strip()
        if text:
            cleaned.append(text)
    return cleaned


def parse_ai_fit_scoring_payload(payload: dict) -> AIFitScoringResult:
    """Validate a local dict payload. No network calls or database writes."""
    if not isinstance(payload, dict):
        raise ValueError("Payload must be a dictionary.")

    errors: list[str] = []
    for field in AI_SCORING_REQUIRED_PAYLOAD_FIELDS:
        if field not in payload:
            errors.append(f"Missing required field: {field}.")

    ai_score: int | None = None
    confidence = ""
    raw_score = payload.get("ai_fit_score")
    try:
        if "ai_fit_score" in payload:
            ai_score = _validate_fit_score_value(raw_score, "ai_fit_score")
    except ValueError as exc:
        errors.append(str(exc))

    raw_confidence = payload.get("confidence")
    if not isinstance(raw_confidence, str):
        errors.append("confidence must be a string: low, medium, or high.")
    else:
        confidence = raw_confidence.strip().lower()
        if confidence not in AI_CONFIDENCE_LEVELS:
            errors.append("confidence must be one of: low, medium, high.")

    raw_label = payload.get("ai_fit_label")
    if not isinstance(raw_label, str) or not raw_label.strip():
        errors.append("ai_fit_label must be a non-empty string.")

    raw_summary = payload.get("reasoning_summary")
    if not isinstance(raw_summary, str):
        errors.append("reasoning_summary must be a string.")
    elif not raw_summary.strip():
        errors.append("reasoning_summary must be a non-empty string.")

    raw_angle = payload.get("recommended_cv_angle")
    if not isinstance(raw_angle, str):
        errors.append("recommended_cv_angle must be a string.")
    elif not raw_angle.strip():
        errors.append("recommended_cv_angle must be a non-empty string.")

    list_fields: dict[str, list[str]] = {}
    for field in (
        "evidence_matches",
        "gaps",
        "deal_breakers",
        "recommended_projects",
        "claim_safety_notes",
    ):
        try:
            list_fields[field] = _parse_string_list_field(payload.get(field), field)
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise ValueError("; ".join(errors))

    assert ai_score is not None
    return AIFitScoringResult(
        ai_fit_score=ai_score,
        ai_fit_label=str(payload["ai_fit_label"]).strip(),
        confidence=confidence,
        evidence_matches=list_fields["evidence_matches"],
        gaps=list_fields["gaps"],
        deal_breakers=list_fields["deal_breakers"],
        reasoning_summary=str(payload["reasoning_summary"]).strip(),
        recommended_cv_angle=str(payload["recommended_cv_angle"]).strip(),
        recommended_projects=list_fields["recommended_projects"],
        manual_review_required=True,
        claim_safety_notes=_merge_ai_scoring_claim_notes(
            list_fields["claim_safety_notes"]
        ),
    )


def build_ai_fit_scoring_result_from_mock(payload: dict) -> AIFitScoringResult:
    """Parse a mocked/static dict payload. Not an OpenAI or external API client."""
    return parse_ai_fit_scoring_payload(payload)


def compare_rule_based_and_ai_scores(
    rule_based_score: int,
    ai_result: AIFitScoringResult,
    threshold: int = AI_SCORE_DISAGREEMENT_THRESHOLD,
) -> AIFitScoreComparison:
    """Side-by-side score comparison. Does not persist data or call external services."""
    validated_rule_score = _validate_fit_score_value(rule_based_score, "rule_based_score")
    score_delta = abs(ai_result.ai_fit_score - validated_rule_score)
    disagreement_flag = score_delta > threshold
    if disagreement_flag:
        disagreement_summary = (
            "Manual review is required because rule-based and AI scores "
            "differ materially."
        )
    else:
        disagreement_summary = (
            "Scores are broadly aligned, but recommendations remain advisory."
        )

    return AIFitScoreComparison(
        rule_based_score=validated_rule_score,
        ai_fit_score=ai_result.ai_fit_score,
        score_delta=score_delta,
        disagreement_flag=disagreement_flag,
        disagreement_summary=disagreement_summary,
        manual_review_required=True,
        claim_safety_notes=list(AI_SCORING_CLAIM_SAFETY_NOTES),
    )


# --- Sprint 32C: OpenAI-shaped wrapper + safe fallback (mocked-first; no network) ---

OPENAI_WRAPPER_PROVIDER_NAME = "Claude"
OPENAI_WRAPPER_TIMEOUT_SECONDS = 20

OPENAI_WRAPPER_CLAIM_SAFETY_NOTES = [
    "Sprint 32C wrapper is mocked-first.",
    "No real OpenAI call is made by default.",
    "No API key is required for tests.",
    "Rule-based scoring remains the fallback.",
    "Manual review is always required.",
    "No application is submitted.",
    "No CV or cover letter is finalized.",
    (
        "No Gmail, Calendar, scraping, recruiter automation, or auto-apply "
        "is used."
    ),
]


@dataclass(frozen=True)
class OpenAIFitScoringWrapperResult:
    ai_result: AIFitScoringResult | None
    used_fallback: bool
    fallback_reason: str
    provider_name: str
    manual_review_required: bool
    claim_safety_notes: list[str]


def _build_openai_wrapper_fallback(fallback_reason: str) -> OpenAIFitScoringWrapperResult:
    return OpenAIFitScoringWrapperResult(
        ai_result=None,
        used_fallback=True,
        fallback_reason=fallback_reason,
        provider_name=OPENAI_WRAPPER_PROVIDER_NAME,
        manual_review_required=True,
        claim_safety_notes=list(OPENAI_WRAPPER_CLAIM_SAFETY_NOTES),
    )


def build_openai_fit_scoring_prompt(
    company_name: str,
    job_title: str,
    location: str,
    job_description: str,
    rule_based_analysis: JobPostingAnalysis,
) -> dict:
    """Build a structured prompt dict for a future provider call. No secrets or network."""
    return {
        "company_name": company_name,
        "job_title": job_title,
        "location": location,
        "job_description": job_description,
        "rule_based_fit_score": rule_based_analysis.fit_score,
        "rule_based_recommendation": rule_based_analysis.recommendation,
        "matched_skills": list(rule_based_analysis.matched_skills),
        "risks": list(rule_based_analysis.risks),
        "deal_breakers": list(rule_based_analysis.deal_breakers),
        "required_output_schema": {
            "fields": list(AI_SCORING_REQUIRED_PAYLOAD_FIELDS),
            "score_range": {"min": 0, "max": 100},
            "confidence_values": sorted(AI_CONFIDENCE_LEVELS),
        },
        "safety_rules": [
            "Output is advisory only.",
            "Manual review is required before saving or using recommendations externally.",
            "Do not claim auto-save, auto-apply, or application submission.",
            "Do not generate a final CV or finalize a cover letter.",
            "Do not invent skills, employers, dates, metrics, or experience.",
            "Do not include Gmail, Calendar, inbox, or contact data.",
        ],
        "provider_name": OPENAI_WRAPPER_PROVIDER_NAME,
        "timeout_seconds": OPENAI_WRAPPER_TIMEOUT_SECONDS,
    }


def build_openai_fit_scoring_with_fallback(
    company_name: str,
    job_title: str,
    location: str,
    job_description: str,
    provider_callable: Callable[[dict], dict] | None = None,
) -> OpenAIFitScoringWrapperResult:
    """
    Rule-based analysis first, then optional injected provider callable.
    Never calls OpenAI directly or writes to the database.
    """
    rule_based_analysis = analyze_job_posting(
        company_name=company_name,
        job_title=job_title,
        location=location,
        job_posting=job_description,
    )

    if provider_callable is None:
        return _build_openai_wrapper_fallback(
            "Provider callable is missing; using rule-based scoring only."
        )

    try:
        prompt = build_openai_fit_scoring_prompt(
            company_name=company_name,
            job_title=job_title,
            location=location,
            job_description=job_description,
            rule_based_analysis=rule_based_analysis,
        )
        provider_response = provider_callable(prompt)
        if not isinstance(provider_response, dict):
            return _build_openai_wrapper_fallback(
                "Provider callable must return a dictionary payload."
            )
        ai_result = parse_ai_fit_scoring_payload(provider_response)
    except ValueError as exc:
        return _build_openai_wrapper_fallback(
            f"Provider payload validation failed: {exc}"
        )
    except Exception as exc:
        return _build_openai_wrapper_fallback(f"Provider callable failed: {exc}")

    return OpenAIFitScoringWrapperResult(
        ai_result=ai_result,
        used_fallback=False,
        fallback_reason="",
        provider_name=OPENAI_WRAPPER_PROVIDER_NAME,
        manual_review_required=True,
        claim_safety_notes=list(OPENAI_WRAPPER_CLAIM_SAFETY_NOTES),
    )


def compare_openai_wrapper_result_with_rule_based(
    rule_based_score: int,
    wrapper_result: OpenAIFitScoringWrapperResult,
) -> AIFitScoreComparison | None:
    """Compare wrapper AI result to rule-based score; None when fallback has no AI result."""
    if wrapper_result.ai_result is None:
        return None
    return compare_rule_based_and_ai_scores(rule_based_score, wrapper_result.ai_result)


def check_cover_letter_quality(
    company_name: str,
    job_title: str,
    job_description: str,
    cover_letter: str,
) -> CoverLetterQualityResult:
    text = cover_letter.lower()
    job_text = normalise_text(company_name, job_title, job_description)
    score = 0
    strengths: list[str] = []
    weaknesses: list[str] = []
    fixes: list[str] = []

    if company_name and company_name.lower() in text:
        score += 15
        strengths.append("Mentions the company by name.")
    else:
        weaknesses.append("Company-specific reason is weak or missing.")
        fixes.append("Add one sentence explaining why this company or domain is relevant.")

    title_tokens = [token for token in job_title.lower().split() if len(token) > 3]
    if title_tokens and any(token in text for token in title_tokens):
        score += 15
        strengths.append("References the target role clearly.")
    else:
        weaknesses.append("Role alignment is not explicit enough.")
        fixes.append(
            "Mention the exact role and connect it to your analytics/reporting "
            "direction."
        )

    project_terms = [
        "bakeops",
        "marketvista",
        "riskwise",
        "tradeintel",
        "databridge",
        "careerfunnel",
    ]
    if any(term in text for term in project_terms):
        score += 20
        strengths.append("Uses portfolio project evidence.")
    else:
        weaknesses.append("No portfolio project evidence is visible.")
        fixes.append(
            "Mention one relevant project, such as BakeOps for KPI/reporting roles "
            "or MarketVista for dashboards."
        )

    business_terms = [
        "kpi",
        "reporting",
        "dashboard",
        "finance",
        "operations",
        "stakeholder",
        "decision",
        "analysis",
    ]
    overlap = [term for term in business_terms if term in text and term in job_text]
    if len(overlap) >= 2:
        score += 20
        strengths.append("Connects to business/reporting language from the role.")
    else:
        weaknesses.append("Business value is not strongly connected to the job description.")
        fixes.append(
            "Add job-specific keywords such as KPI reporting, dashboards, "
            "stakeholder analysis, or finance operations where truthful."
        )

    if 120 <= len(cover_letter.split()) <= 320:
        score += 15
        strengths.append("Length is suitable for a concise application message.")
    else:
        weaknesses.append("Length may be too short or too long.")
        fixes.append("Aim for a concise 3–5 paragraph letter with evidence, fit, and interest.")

    risky_claims = ["expert", "master", "guaranteed", "best candidate", "10 years of data"]
    if any(claim in text for claim in risky_claims):
        weaknesses.append("Contains potentially exaggerated wording.")
        fixes.append("Replace exaggerated claims with evidence-based project or work examples.")
        evidence_warning = "Review exaggerated claims before using this letter."
    else:
        score += 15
        evidence_warning = (
            "No obvious exaggeration detected; still verify every claim before sending."
        )

    score = max(0, min(100, score))
    if score >= 80:
        label = "Strong"
    elif score >= 60:
        label = "Good but needs tailoring"
    elif score >= 40:
        label = "Needs improvement"
    else:
        label = "Weak"

    return CoverLetterQualityResult(score, label, strengths, weaknesses, fixes, evidence_warning)


def analyze_rejection_patterns(user) -> RejectionPatternReport:
    rejected_statuses = [ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED]
    rejected = list(JobApplication.objects.filter(user=user, status__in=rejected_statuses))
    total = len(rejected)
    if total == 0:
        return RejectionPatternReport(
            total_rejections=0,
            headline="No rejection pattern yet",
            patterns=["There are no rejected or auto-rejected applications to analyze."],
            likely_causes=[],
            recommendations=["Keep logging outcomes so patterns become visible."],
            highest_risk_cv_versions=[],
            highest_risk_sources=[],
            highest_risk_role_terms=[],
        )

    cv_counter = Counter(app.cv_version or "Missing CV version" for app in rejected)
    source_counter = Counter(app.get_source_display() for app in rejected)
    role_terms = Counter()
    causes: list[str] = []
    for app in rejected:
        text = normalise_text(app.job_title, app.required_skills, app.job_description, app.notes)
        for term in [
            "senior",
            "analytics engineer",
            "data engineer",
            "dbt",
            "snowflake",
            "aws",
            "power bi",
            "sql",
            "finance",
        ]:
            if term in text:
                role_terms[term] += 1
        if any(term in text for term in ["senior", "3+ years", "5+ years"]):
            causes.append("Seniority mismatch appears in rejected roles.")
        if any(term in text for term in HARD_GAP_TERMS):
            causes.append("Hard-tool gap appears in rejected roles.")

    patterns = [
        f"{total} rejected/auto-rejected application(s) found.",
        f"Most common rejected CV version: {cv_counter.most_common(1)[0][0]}.",
        f"Most common rejected source: {source_counter.most_common(1)[0][0]}.",
    ]
    if role_terms:
        patterns.append(
            "Frequent rejected role signals: "
            + ", ".join(term for term, _ in role_terms.most_common(5))
            + "."
        )

    recommendations = [
        "Pause or reduce applications in the highest-risk role/source/CV "
        "combinations until evidence improves.",
        "Record rejection reason when known; unknown rejections are harder to learn from.",
        "Prioritise junior Data Analyst, Reporting Analyst, BI Analyst, and Finance "
        "Data Analyst roles before senior AE/DE roles.",
    ]
    if any("Hard-tool" in cause for cause in causes):
        recommendations.append(
            "Strengthen or de-emphasise cloud/dbt/Snowflake-heavy roles unless "
            "listed as optional."
        )

    return RejectionPatternReport(
        total_rejections=total,
        headline="AI Rejection Pattern Analysis",
        patterns=patterns,
        likely_causes=list(dict.fromkeys(causes))
        or [
            "No single obvious cause yet; add more rejection reasons and job "
            "requirements."
        ],
        recommendations=recommendations,
        highest_risk_cv_versions=[f"{cv}: {count}" for cv, count in cv_counter.most_common(5)],
        highest_risk_sources=[
            f"{source}: {count}" for source, count in source_counter.most_common(5)
        ],
        highest_risk_role_terms=[f"{term}: {count}" for term, count in role_terms.most_common(6)],
    )


def build_cv_ab_testing_rows(user) -> list[CVVersionPerformanceRow]:
    apps = JobApplication.objects.filter(user=user).exclude(cv_version="")
    grouped: dict[str, list[JobApplication]] = defaultdict(list)
    for app in apps:
        grouped[app.cv_version].append(app)

    rows: list[CVVersionPerformanceRow] = []
    response_statuses = {
        ApplicationStatus.ACKNOWLEDGED,
        ApplicationStatus.SCREENING_CALL,
        ApplicationStatus.TECHNICAL_SCREEN,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.AUTO_REJECTED,
    }
    for cv, records in grouped.items():
        total = len(records)
        responses = sum(
            1 for app in records if app.status in response_statuses or app.response_date
        )
        interviews = sum(
            1
            for app in records
            if app.status in [ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER]
        )
        offers = sum(1 for app in records if app.status == ApplicationStatus.OFFER)
        rejections = sum(
            1
            for app in records
            if app.status in [ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED]
        )
        response_rate = safe_percentage(responses, total)
        interview_rate = safe_percentage(interviews, total)
        offer_rate = safe_percentage(offers, total)
        if total < 3:
            recommendation = "Not enough sample size yet."
        elif response_rate >= 25:
            recommendation = "Promising CV version — keep using for matching roles."
        elif response_rate == 0:
            recommendation = "Underperforming so far — review targeting or CV positioning."
        else:
            recommendation = "Mixed result — compare against role type and source."
        rows.append(
            CVVersionPerformanceRow(
                cv,
                total,
                responses,
                interviews,
                offers,
                rejections,
                response_rate,
                interview_rate,
                offer_rate,
                recommendation,
            )
        )

    return sorted(rows, key=lambda row: (row.response_rate, row.applications), reverse=True)


def build_smart_notifications(user, limit: int = 20) -> list[SmartNotification]:
    today = timezone.localdate()
    notifications: list[SmartNotification] = []

    overdue_followups = JobApplication.objects.filter(user=user, follow_up_date__lt=today).exclude(
        follow_up_status__in=[
            FollowUpStatus.SENT,
            FollowUpStatus.RESPONDED,
            FollowUpStatus.NOT_NEEDED,
        ]
    )[:5]
    for app in overdue_followups:
        notifications.append(
            SmartNotification(
                priority="High",
                title=f"Overdue follow-up: {app.company_name}",
                message=f"Follow-up was due on {app.follow_up_date} for {app.job_title}.",
                recommended_action="Send a follow-up message or update the follow-up status.",
                related_url=app.get_absolute_url(),
            )
        )

    due_today = JobApplication.objects.filter(user=user, follow_up_date=today).exclude(
        follow_up_status__in=[
            FollowUpStatus.SENT,
            FollowUpStatus.RESPONDED,
            FollowUpStatus.NOT_NEEDED,
        ]
    )[:5]
    for app in due_today:
        notifications.append(
            SmartNotification(
                priority="High",
                title=f"Follow-up due today: {app.company_name}",
                message=f"{app.job_title} is ready for a polite check-in.",
                recommended_action="Use the AI Follow-Up Writer and log the contact date.",
                related_url=app.get_absolute_url(),
            )
        )

    for app in JobApplication.objects.filter(user=user, cv_version="")[:5]:
        notifications.append(
            SmartNotification(
                priority="Medium",
                title="Missing CV version",
                message=f"{app.company_name} — {app.job_title} has no CV version recorded.",
                recommended_action="Add the CV version so CV A/B testing remains reliable.",
                related_url=app.get_absolute_url(),
            )
        )

    for app in JobApplication.objects.filter(user=user, job_url="")[:5]:
        notifications.append(
            SmartNotification(
                priority="Low",
                title="Missing job URL",
                message=f"{app.company_name} — {app.job_title} has no saved job URL.",
                recommended_action="Add the URL if available for future review and evidence.",
                related_url=app.get_absolute_url(),
            )
        )

    upcoming_interviews = InterviewPrep.objects.filter(
        user=user,
        interview_date__gte=today,
        interview_date__lte=today + timedelta(days=5),
    )[:5]
    for interview in upcoming_interviews:
        if interview.readiness_score < 80:
            notifications.append(
                SmartNotification(
                    priority="High",
                    title=f"Interview prep incomplete: {interview.application.company_name}",
                    message=(
                        f"Readiness score is {interview.readiness_score}% for "
                        f"interview on {interview.interview_date}."
                    ),
                    recommended_action=(
                        "Complete checklist items and prepare one project walkthrough."
                    ),
                    related_url=interview.get_absolute_url(),
                )
            )

    if not DailyLog.objects.filter(user=user, log_date=today).exists():
        notifications.append(
            SmartNotification(
                priority="Medium",
                title="Today’s daily log is missing",
                message="No daily activity has been logged for today.",
                recommended_action=(
                    "Add today’s target, actual applications, and blocker notes "
                    "before you stop working."
                ),
            )
        )

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    if (
        today == week_end
        and not WeeklyReview.objects.filter(user=user, week_ending=today).exists()
    ):
        notifications.append(
            SmartNotification(
                priority="Medium",
                title="Weekly review due",
                message="Today is the end of the current week and no weekly review exists yet.",
                recommended_action=(
                    "Complete the weekly review and compare it with the AI Weekly Coach."
                ),
            )
        )

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(notifications, key=lambda n: priority_rank.get(n.priority, 9))[:limit]
