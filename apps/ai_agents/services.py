from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from apps.applications.choices import ApplicationStatus, FollowUpStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.interviews.models import InterviewPrep
from apps.metrics.services import build_funnel_metrics, diagnose_funnel, safe_percentage
from apps.weekly_review.models import WeeklyReview

TARGET_TITLES = [
    "data analyst",
    "junior data analyst",
    "graduate data analyst",
    "reporting analyst",
    "bi analyst",
    "business intelligence analyst",
    "insights analyst",
    "finance data analyst",
    "operations data analyst",
]
SENIOR_SIGNALS = ["senior", "lead", "principal", "head of", "manager", "5+ years", "minimum 5", "3+ years", "minimum 3"]
LOCATION_SIGNALS = ["london", "croydon", "south london", "remote uk", "hybrid london", "purley"]
CORE_SKILLS = ["python", "sql", "excel", "reporting", "dashboard", "power bi", "analytics", "pandas", "etl", "kpi", "stakeholder", "finance", "reconciliation"]
DEAL_BREAKERS = ["dbt required", "spark", "kafka", "airflow", "aws redshift", "sc clearance", "dv clearance", "cima", "acca", "aca"]


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


def analyze_job_posting(company_name: str, job_title: str, location: str, job_posting: str) -> JobPostingAnalysis:
    text = normalise_text(company_name, job_title, location, job_posting)
    score = 0
    risks: list[str] = []

    if any(title in text for title in TARGET_TITLES):
        score += 25
    else:
        risks.append("Role title is not clearly one of the preferred junior data/reporting/BI targets.")

    if any(signal in text for signal in LOCATION_SIGNALS):
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

    matched_skills = [skill for skill in CORE_SKILLS if skill in text]
    score += min(25, len(matched_skills) * 4)

    found_deal_breakers = [breaker for breaker in DEAL_BREAKERS if breaker in text]
    if found_deal_breakers:
        score -= 25
        risks.append("Hard requirement or deal-breaker signals detected.")
    else:
        score += 10

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
        cover_letter_focus.append("Make SQL/database evidence visible through models, queries, or reporting outputs.")
    if "excel" in matched_skills:
        cover_letter_focus.append("Mention advanced Excel, reporting discipline, and operational accuracy.")

    next_actions = [
        "Save the role in Applications if the fit score is acceptable.",
        f"Use {recommended_cv} as the starting CV version.",
        "Select the strongest matching portfolio project before drafting the cover letter.",
        "Set a follow-up date 7 working days after submission.",
    ]

    explanation = (
        "This analysis is a local rule-based AI-style assessment. It uses role title, seniority, location, skill keywords, "
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
    if any(word in text for word in ["finance", "risk", "reconciliation", "ledger", "fx", "payment", "banking"]):
        return "Finance_DA_CV_v1"
    if any(word in text for word in ["bi", "dashboard", "power bi", "reporting", "insights", "kpi"]):
        return "BI_Reporting_CV_v1"
    if any(word in text for word in ["etl", "api", "pipeline", "analytics engineer", "data product"]):
        return "AE_Data_Product_CV_v1"
    return "DA_CV_v2"


def recommend_projects_from_text(text: str) -> list[str]:
    if any(word in text for word in ["finance", "risk", "trading", "market", "banking"]):
        return ["TradeIntel 360", "RiskWise Planner", "MarketVista Dashboard"]
    if any(word in text for word in ["operations", "kpi", "margin", "waste", "product performance"]):
        return ["BakeOps Intelligence", "CareerFunnel Tracker", "MarketVista Dashboard"]
    if any(word in text for word in ["etl", "api", "pipeline", "integration"]):
        return ["DataBridge Market API", "MarketVista Dashboard", "TradeIntel 360"]
    return ["BakeOps Intelligence", "MarketVista Dashboard", "CareerFunnel Tracker"]


def build_next_best_actions(user, limit: int = 8) -> list[AgentAction]:
    today = timezone.localdate()
    actions: list[AgentAction] = []

    due_followups = JobApplication.objects.filter(user=user, follow_up_date__lte=today).exclude(
        follow_up_status__in=[FollowUpStatus.SENT, FollowUpStatus.RESPONDED, FollowUpStatus.NOT_NEEDED]
    )[:5]
    for app in due_followups:
        actions.append(
            AgentAction(
                priority="High",
                title=f"Follow up with {app.company_name}",
                reason=f"Follow-up date was {app.follow_up_date} and status is {app.get_follow_up_status_display()}.",
                recommended_action="Send a short, polite follow-up and update the follow-up status.",
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
                reason=f"Interview is scheduled for {interview.interview_date}; readiness score is {interview.readiness_score}%.",
                recommended_action="Complete the interview checklist and prepare one project walkthrough.",
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
                recommended_action="Apply to suitable junior Data Analyst, Reporting Analyst, BI Analyst, or Finance Data Analyst roles.",
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
        f"I hope you are well. I wanted to follow up on my application for the {application.job_title} role at {application.company_name}, "
        f"submitted on {application.date_applied}.\n\n"
        "I remain very interested in the opportunity because it aligns with my experience in reporting, KPI analysis, "
        "Python/Django analytics projects, and business-facing data work.\n\n"
        "Please let me know if there is any further information I can provide.\n\n"
        "Kind regards,\n"
        "Aminul Islam"
    )
    reason = "Generated because the application is ready for a polite status check without sounding pushy."
    return FollowUpDraft(subject=subject, body=body, reason=reason)


def generate_interview_prep(application: JobApplication) -> InterviewPrepPack:
    text = normalise_text(application.job_title, application.required_skills, application.job_description, application.notes)
    projects = recommend_projects_from_text(text)
    cv = recommend_cv_from_text(text)
    profile_angle = (
        f"Position yourself as a finance/operations professional moving into analytics, using {cv} and evidence from "
        f"{projects[0]} to show practical KPI, reporting, and decision-support capability."
    )
    likely_questions = [
        "Tell me about yourself and your move into data analytics.",
        f"Why are you interested in the {application.job_title} role at {application.company_name}?",
        "Walk me through one analytics project from problem to business output.",
        "How do you handle messy or incomplete data?",
        "How have you used Excel, Python, SQL, or dashboards in practical work?",
        "What would you do if a stakeholder challenged your analysis?",
    ]
    technical_topics = ["Excel lookups/pivots", "SQL filtering and joins", "Python/pandas data cleaning", "KPI definitions", "Dashboard interpretation"]
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
        wins.append(f"Response rate is {metrics.response_rate}%, which suggests some targeting is working.")
    if metrics.interview_rate > 0:
        wins.append("The funnel has reached interview stage, so CV/screening evidence is not completely failing.")
    if hit_days > 0:
        wins.append(f"You hit the daily target on {hit_days} logged day(s) this week.")

    if target and actual < target:
        risks.append(f"Application volume is below target: {actual}/{target} this week.")
    if metrics.response_rate < 10 and metrics.total_applications >= 10:
        risks.append("Response rate is still weak; CV positioning or role targeting needs review.")
    if JobApplication.objects.filter(user=user, follow_up_date__lte=today).exclude(
        follow_up_status__in=[FollowUpStatus.SENT, FollowUpStatus.RESPONDED, FollowUpStatus.NOT_NEEDED]
    ).exists():
        risks.append("There are overdue follow-ups that may be costing momentum.")

    if not wins:
        wins.append("The main win is that the platform now has data to diagnose rather than guessing.")
    if not risks:
        risks.append("No major weekly risk is obvious yet; keep logging consistently.")

    next_week_plan = [
        "Set a realistic weekly application target and protect time for submissions.",
        "Prioritise junior Data Analyst, Reporting Analyst, BI Analyst, and Finance Data Analyst roles.",
        "Use the AI Job Posting Analyzer before applying to reduce weak-fit applications.",
        "Prepare interview evidence around projects, not only technical tools.",
    ]
    avoid_next_week = [
        "Avoid senior roles with hard 3+ or 5+ year requirements unless the fit is unusually strong.",
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

# --- Advanced Smart AI Assistance Layer ---

from collections import Counter, defaultdict


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
    "python", "sql", "excel", "power bi", "tableau", "dashboard", "reporting", "kpi",
    "pandas", "etl", "api", "data quality", "stakeholder", "finance", "reconciliation",
    "analytics", "data modelling", "visualisation", "statistics", "snowflake", "dbt", "aws",
]

USER_EVIDENCE_MAP = {
    "python": "Python portfolio projects and data-processing workflows",
    "django": "Django-based analytics platforms including BakeOps, MarketVista, RiskWise, and CareerFunnel",
    "excel": "Advanced Excel, cashflow platform, scorecards, formulas, and reporting experience",
    "reporting": "Operational reporting, KPI tracking, and monthly performance reporting experience",
    "dashboard": "MarketVista, BakeOps, and CareerFunnel dashboard pages",
    "kpi": "KPI modelling in BakeOps Intelligence and operational reporting roles",
    "finance": "Money transfer, FX, remittance, reconciliations, and finance operations background",
    "reconciliation": "FX/remittance operations and audit-ready cashflow records",
    "pandas": "Python/pandas analytics project work",
    "etl": "DataBridge Market API and analytics ETL-style workflows",
    "api": "Django API-style JSON endpoints and market-data ingestion projects",
    "stakeholder": "Agent training, operational support, and business-facing reporting experience",
    "sql": "Database-backed Django projects and dashboard-ready data models; strengthen explicit SQL examples if needed",
}

HARD_GAP_TERMS = ["dbt", "snowflake", "airflow", "spark", "kafka", "aws redshift", "sc clearance", "dv clearance"]


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
            if skill in ["sql", "power bi", "tableau", "dbt", "snowflake", "aws"] and skill not in evidence_text:
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
        claims_to_avoid.append("Do not position this as a junior-friendly role without checking the seniority requirement.")

    if score >= 75:
        recommendation = "Strong enough to apply if seniority and location also fit."
    elif score >= 55:
        recommendation = "Apply selectively; tailor the CV around the strongest evidence and acknowledge weaker tools carefully."
    else:
        recommendation = "Weak fit; skip unless the missing skills are clearly optional."

    return CVGapAnalysis(
        score=score,
        matched_skills=matched,
        partial_matches=partial,
        missing_skills=sorted(set(missing)),
        evidence_to_emphasise=list(dict.fromkeys(evidence_to_emphasise))[:8],
        keywords_to_add_honestly=keywords_to_add,
        claims_to_avoid=claims_to_avoid or ["Avoid exaggerating tool depth; keep evidence project-based and realistic."],
        recommendation=recommendation,
    )


def check_cover_letter_quality(company_name: str, job_title: str, job_description: str, cover_letter: str) -> CoverLetterQualityResult:
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
        fixes.append("Mention the exact role and connect it to your analytics/reporting direction.")

    project_terms = ["bakeops", "marketvista", "riskwise", "tradeintel", "databridge", "careerfunnel"]
    if any(term in text for term in project_terms):
        score += 20
        strengths.append("Uses portfolio project evidence.")
    else:
        weaknesses.append("No portfolio project evidence is visible.")
        fixes.append("Mention one relevant project, such as BakeOps for KPI/reporting roles or MarketVista for dashboards.")

    business_terms = ["kpi", "reporting", "dashboard", "finance", "operations", "stakeholder", "decision", "analysis"]
    overlap = [term for term in business_terms if term in text and term in job_text]
    if len(overlap) >= 2:
        score += 20
        strengths.append("Connects to business/reporting language from the role.")
    else:
        weaknesses.append("Business value is not strongly connected to the job description.")
        fixes.append("Add job-specific keywords such as KPI reporting, dashboards, stakeholder analysis, or finance operations where truthful.")

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
        evidence_warning = "No obvious exaggeration detected; still verify every claim before sending."

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
        for term in ["senior", "analytics engineer", "data engineer", "dbt", "snowflake", "aws", "power bi", "sql", "finance"]:
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
        patterns.append("Frequent rejected role signals: " + ", ".join(term for term, _ in role_terms.most_common(5)) + ".")

    recommendations = [
        "Pause or reduce applications in the highest-risk role/source/CV combinations until evidence improves.",
        "Record rejection reason when known; unknown rejections are harder to learn from.",
        "Prioritise junior Data Analyst, Reporting Analyst, BI Analyst, and Finance Data Analyst roles before senior AE/DE roles.",
    ]
    if any("Hard-tool" in cause for cause in causes):
        recommendations.append("Strengthen or de-emphasise cloud/dbt/Snowflake-heavy roles unless listed as optional.")

    return RejectionPatternReport(
        total_rejections=total,
        headline="AI Rejection Pattern Analysis",
        patterns=patterns,
        likely_causes=list(dict.fromkeys(causes)) or ["No single obvious cause yet; add more rejection reasons and job requirements."],
        recommendations=recommendations,
        highest_risk_cv_versions=[f"{cv}: {count}" for cv, count in cv_counter.most_common(5)],
        highest_risk_sources=[f"{source}: {count}" for source, count in source_counter.most_common(5)],
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
        responses = sum(1 for app in records if app.status in response_statuses or app.response_date)
        interviews = sum(1 for app in records if app.status in [ApplicationStatus.INTERVIEW, ApplicationStatus.OFFER])
        offers = sum(1 for app in records if app.status == ApplicationStatus.OFFER)
        rejections = sum(1 for app in records if app.status in [ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED])
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
        rows.append(CVVersionPerformanceRow(cv, total, responses, interviews, offers, rejections, response_rate, interview_rate, offer_rate, recommendation))

    return sorted(rows, key=lambda row: (row.response_rate, row.applications), reverse=True)


def build_smart_notifications(user, limit: int = 20) -> list[SmartNotification]:
    today = timezone.localdate()
    notifications: list[SmartNotification] = []

    overdue_followups = JobApplication.objects.filter(user=user, follow_up_date__lt=today).exclude(
        follow_up_status__in=[FollowUpStatus.SENT, FollowUpStatus.RESPONDED, FollowUpStatus.NOT_NEEDED]
    )[:5]
    for app in overdue_followups:
        notifications.append(SmartNotification(
            priority="High",
            title=f"Overdue follow-up: {app.company_name}",
            message=f"Follow-up was due on {app.follow_up_date} for {app.job_title}.",
            recommended_action="Send a follow-up message or update the follow-up status.",
            related_url=app.get_absolute_url(),
        ))

    due_today = JobApplication.objects.filter(user=user, follow_up_date=today).exclude(
        follow_up_status__in=[FollowUpStatus.SENT, FollowUpStatus.RESPONDED, FollowUpStatus.NOT_NEEDED]
    )[:5]
    for app in due_today:
        notifications.append(SmartNotification(
            priority="High",
            title=f"Follow-up due today: {app.company_name}",
            message=f"{app.job_title} is ready for a polite check-in.",
            recommended_action="Use the AI Follow-Up Writer and log the contact date.",
            related_url=app.get_absolute_url(),
        ))

    for app in JobApplication.objects.filter(user=user, cv_version="")[:5]:
        notifications.append(SmartNotification(
            priority="Medium",
            title="Missing CV version",
            message=f"{app.company_name} — {app.job_title} has no CV version recorded.",
            recommended_action="Add the CV version so CV A/B testing remains reliable.",
            related_url=app.get_absolute_url(),
        ))

    for app in JobApplication.objects.filter(user=user, job_url="")[:5]:
        notifications.append(SmartNotification(
            priority="Low",
            title="Missing job URL",
            message=f"{app.company_name} — {app.job_title} has no saved job URL.",
            recommended_action="Add the URL if available for future review and evidence.",
            related_url=app.get_absolute_url(),
        ))

    upcoming_interviews = InterviewPrep.objects.filter(user=user, interview_date__gte=today, interview_date__lte=today + timedelta(days=5))[:5]
    for interview in upcoming_interviews:
        if interview.readiness_score < 80:
            notifications.append(SmartNotification(
                priority="High",
                title=f"Interview prep incomplete: {interview.application.company_name}",
                message=f"Readiness score is {interview.readiness_score}% for interview on {interview.interview_date}.",
                recommended_action="Complete checklist items and prepare one project walkthrough.",
                related_url=interview.get_absolute_url(),
            ))

    if not DailyLog.objects.filter(user=user, log_date=today).exists():
        notifications.append(SmartNotification(
            priority="Medium",
            title="Today’s daily log is missing",
            message="No daily activity has been logged for today.",
            recommended_action="Add today’s target, actual applications, and blocker notes before you stop working.",
        ))

    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    if today == week_end and not WeeklyReview.objects.filter(user=user, week_ending=today).exists():
        notifications.append(SmartNotification(
            priority="Medium",
            title="Weekly review due",
            message="Today is the end of the current week and no weekly review exists yet.",
            recommended_action="Complete the weekly review and compare it with the AI Weekly Coach.",
        ))

    priority_rank = {"High": 0, "Medium": 1, "Low": 2}
    return sorted(notifications, key=lambda n: priority_rank.get(n.priority, 9))[:limit]
