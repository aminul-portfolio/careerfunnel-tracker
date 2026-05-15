from __future__ import annotations

from dataclasses import dataclass

from apps.applications.choices import RoleFit, WorkType
from apps.applications.models import JobApplication

from .constants import (
    BAD_TITLE_WORDS,
    DEAL_BREAKERS,
    GOOD_LOCATION_WORDS,
    GOOD_SKILLS,
    TARGET_TITLES,
)


@dataclass(frozen=True)
class SmartApplicationReview:
    job_fit_score: int
    job_fit_label: str
    job_fit_reasons: list[str]
    recommended_cv: str
    recommended_cv_reason: str
    recommended_projects: list[str]
    project_reason: str
    readiness_score: int
    readiness_missing_items: list[str]
    next_action: str


def _text(application: JobApplication) -> str:
    return " ".join([
        application.job_title or "",
        application.location or "",
        application.experience_level or "",
        application.required_skills or "",
        application.job_description or "",
        application.notes or "",
    ]).lower()


def calculate_job_fit_score(application: JobApplication) -> tuple[int, list[str]]:
    text = _text(application)
    score = 0
    reasons: list[str] = []

    if any(title in text for title in TARGET_TITLES) and not any(
        word in text for word in BAD_TITLE_WORDS
    ):
        score += 25
        reasons.append("Target role title appears suitable.")
    elif application.role_fit == RoleFit.STRONG:
        score += 20
        reasons.append("Role fit was manually marked as strong.")
    elif application.role_fit == RoleFit.MEDIUM:
        score += 12
        reasons.append("Role fit is medium, so it may be worth selective effort.")

    if application.work_type in {
        WorkType.REMOTE,
        WorkType.HYBRID,
        WorkType.FLEXIBLE,
    } or any(word in text for word in GOOD_LOCATION_WORDS):
        score += 20
        reasons.append("Location/work pattern appears workable.")

    if any(level in text for level in ["junior", "graduate", "entry", "0-2", "1-2", "trainee"]):
        score += 20
        reasons.append("Experience level appears junior-friendly.")

    matched_skills = [skill for skill in GOOD_SKILLS if skill in text]
    if matched_skills:
        score += min(25, len(matched_skills) * 4)
        reasons.append("Relevant skills found: " + ", ".join(matched_skills[:6]) + ".")

    if not any(word in text for word in DEAL_BREAKERS):
        score += 10
        reasons.append("No obvious deal-breaker detected.")
    else:
        score -= 20
        reasons.append("Potential deal-breaker detected. Review carefully before applying.")

    score = max(0, min(100, score))
    return score, reasons


def fit_label(score: int) -> str:
    if score >= 80:
        return "Strong — Apply"
    if score >= 60:
        return "Good — Apply selectively"
    if score >= 40:
        return "Weak — Review before applying"
    return "Skip / low fit"


def recommend_cv(application: JobApplication) -> tuple[str, str]:
    text = _text(application)
    if any(
        word in text
        for word in [
            "finance",
            "risk",
            "ledger",
            "reconciliation",
            "fx",
            "reporting analyst",
        ]
    ):
        return (
            "Finance_DA_CV_v1",
            "Finance/reporting language appears in the role. "
            "Use finance operations and KPI evidence.",
        )
    if any(word in text for word in ["bi", "dashboard", "power bi", "reporting", "insights"]):
        return (
            "BI_Reporting_CV_v1",
            "The role appears dashboard/reporting focused. "
            "Emphasise metrics, dashboards, and reporting outputs.",
        )
    if any(
        word in text
        for word in ["analytics engineer", "etl", "data product", "pipeline", "api"]
    ):
        return (
            "AE_Data_Product_CV_v1",
            "The role mentions engineering/data-product signals. "
            "Emphasise ETL, API, and data-product projects.",
        )
    return (
        "DA_CV_v2",
        "Default to the Data Analyst CV because the role does not clearly require "
        "a specialist CV.",
    )


def recommend_projects(application: JobApplication) -> tuple[list[str], str]:
    text = _text(application)
    if any(word in text for word in ["finance", "risk", "trading", "market", "portfolio"]):
        return (
            ["TradeIntel 360", "RiskWise Planner", "MarketVista Dashboard"],
            "Finance/risk context detected. Use FinTech analytics evidence.",
        )
    if any(word in text for word in ["operations", "kpi", "waste", "product", "margin"]):
        return (
            [
                "BakeOps Intelligence",
                "CareerFunnel Tracker",
                "MarketVista Dashboard",
            ],
            "Operational analytics context detected. "
            "Use KPI and decision-support projects.",
        )
    if any(word in text for word in ["api", "etl", "pipeline", "integration"]):
        return (
            ["DataBridge Market API", "MarketVista Dashboard", "TradeIntel 360"],
            "Data ingestion or ETL signals detected. Use pipeline/API projects.",
        )
    return (
        ["BakeOps Intelligence", "MarketVista Dashboard", "CareerFunnel Tracker"],
        "General analytics role detected. "
        "Use broad dashboard, KPI, and workflow evidence.",
    )


def calculate_readiness(application: JobApplication) -> tuple[int, list[str]]:
    checks = {
        "CV version selected": bool(application.cv_version),
        "CV tailored": application.is_cv_tailored,
        "Cover letter version selected": bool(application.cover_letter_version),
        "Cover letter tailored": application.is_cover_letter_tailored,
        "Portfolio project included": application.portfolio_project_included,
        "Company researched": application.company_researched,
        "Role fit marked strong or medium": application.role_fit
        in {RoleFit.STRONG, RoleFit.MEDIUM},
        "Job URL saved": bool(application.job_url),
        "Follow-up date set": bool(application.follow_up_date),
        "Required skills captured": bool(application.required_skills),
    }
    passed = sum(1 for value in checks.values() if value)
    missing = [label for label, value in checks.items() if not value]
    return int((passed / len(checks)) * 100), missing


def determine_next_action(application: JobApplication, score: int, readiness: int) -> str:
    if score < 40:
        return "Review fit carefully before spending time on this application."
    if readiness < 70:
        return "Complete missing readiness items before submitting or following up."
    if application.is_follow_up_due:
        return "Send a polite follow-up today."
    if application.status in {"screening_call", "technical_screen", "interview"}:
        return "Prepare interview answers and project walkthrough evidence."
    return (
        application.next_action
        or "Application looks ready. Submit or monitor the next response."
    )


def build_smart_review(application: JobApplication) -> SmartApplicationReview:
    score, reasons = calculate_job_fit_score(application)
    cv, cv_reason = recommend_cv(application)
    projects, project_reason = recommend_projects(application)
    readiness, missing = calculate_readiness(application)
    next_action = determine_next_action(application, score, readiness)
    return SmartApplicationReview(
        job_fit_score=score,
        job_fit_label=fit_label(score),
        job_fit_reasons=reasons,
        recommended_cv=cv,
        recommended_cv_reason=cv_reason,
        recommended_projects=projects,
        project_reason=project_reason,
        readiness_score=readiness,
        readiness_missing_items=missing,
        next_action=next_action,
    )


def build_smart_review_rows(user):
    applications = JobApplication.objects.filter(user=user)
    rows = []
    for application in applications:
        rows.append({"application": application, "review": build_smart_review(application)})
    return rows
