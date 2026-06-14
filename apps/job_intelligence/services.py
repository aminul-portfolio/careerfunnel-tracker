from __future__ import annotations

from dataclasses import dataclass

from apps.applications.choices import RoleFit, WorkType
from apps.applications.models import JobApplication

from .constants import (
    BAD_TITLE_WORDS,
    DEAL_BREAKERS,
    GOOD_LOCATION_WORDS,
    GOOD_SKILLS,
    LEARNING_TARGETS,
    TARGET_TITLES,
)

# Role-specific CV angle advice belongs in Sprint 31; saved CV filename is locked.
LOCKED_CV = "Aminul_Islam_Data_Analyst_CV"


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
        return "Strong - Apply"
    if score >= 60:
        return "Good - Apply selectively"
    if score >= 40:
        return "Weak - Review before applying"
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
            LOCKED_CV,
            "Finance/reporting language appears in the role. "
            "Use finance operations and KPI evidence.",
        )
    if any(word in text for word in ["bi", "dashboard", "power bi", "reporting", "insights"]):
        return (
            LOCKED_CV,
            "The role appears dashboard/reporting focused. "
            "Emphasise metrics, dashboards, and reporting outputs.",
        )
    if any(
        word in text
        for word in ["analytics engineer", "etl", "data product", "pipeline", "api"]
    ):
        return (
            LOCKED_CV,
            "The role mentions engineering/data-product signals. "
            "Emphasise ETL, API, and data-product projects.",
        )
    return (
        LOCKED_CV,
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


# --- Sprint 41 Skill Intelligence Foundation ---

_SKILL_INTELLIGENCE_ADVISORY = (
    "Skill Intelligence is manual, advisory, and evidence-based. It helps you "
    "review role requirements, skills, evidence, and gaps before applying. "
    "It does not make hiring decisions, rewrite CVs, auto-apply, or use "
    "predictive AI/ML."
)

_SKILL_TRUST_POINTS = (
    "Read-only GET page - viewing this screen does not update applications.",
    "Skill mentions are counted from text you already saved on application records.",
    "Gap prompts are review reminders, not grades, predictions, or rejections.",
    "No automatic CV rewriting, submission, or interview prep creation.",
)


@dataclass(frozen=True)
class ManualWorkflowLink:
    label: str
    url: str


@dataclass(frozen=True)
class SkillCategoryEvidence:
    name: str
    evidence_summary: str
    portfolio_projects: tuple[str, ...]
    career_evidence_note: str
    matched_in_applications: int


@dataclass(frozen=True)
class SkillGapPrompt:
    skill_or_area: str
    prompt: str
    context: str


@dataclass(frozen=True)
class ReadinessChecklistItem:
    label: str
    guidance: str


@dataclass(frozen=True)
class RoleReadinessChecklist:
    role_key: str
    role_title: str
    summary: str
    items: tuple[ReadinessChecklistItem, ...]


@dataclass(frozen=True)
class PortfolioSkillMapping:
    project_name: str
    skills_demonstrated: tuple[str, ...]
    manual_note: str
    career_evidence_url: str


@dataclass(frozen=True)
class SkillIntelligenceContext:
    advisory_copy: str
    trust_points: tuple[str, ...]
    application_count: int
    skill_evidence: tuple[SkillCategoryEvidence, ...]
    skill_gaps: tuple[SkillGapPrompt, ...]
    role_checklists: tuple[RoleReadinessChecklist, ...]
    portfolio_mappings: tuple[PortfolioSkillMapping, ...]
    manual_actions: tuple[ManualWorkflowLink, ...]


_SKILL_CATALOG: tuple[dict, ...] = (
    {
        "name": "Python",
        "keywords": ("python", "pandas"),
        "summary": "Scripting and analysis workflows in portfolio projects and applications.",
        "projects": ("CareerFunnel Tracker", "BakeOps Intelligence", "MarketVista Dashboard"),
        "evidence_note": "Career Evidence project report and application keyword matches.",
    },
    {
        "name": "SQL",
        "keywords": ("sql", "query", "database"),
        "summary": "Structured querying for reporting, KPI checks, and data preparation.",
        "projects": ("MarketVista Dashboard", "BakeOps Intelligence"),
        "evidence_note": "Job fit matrix and logged application requirements.",
    },
    {
        "name": "Excel",
        "keywords": ("excel", "spreadsheet"),
        "summary": "Spreadsheet analysis and stakeholder-friendly tables.",
        "projects": ("BakeOps Intelligence",),
        "evidence_note": "Operational analytics and finance-style reporting evidence.",
    },
    {
        "name": "Django",
        "keywords": ("django",),
        "summary": "Web application delivery for tracker and portfolio tooling.",
        "projects": ("CareerFunnel Tracker",),
        "evidence_note": "CareerFunnel Tracker implementation evidence.",
    },
    {
        "name": "Data analysis",
        "keywords": ("data analysis", "data analyst", "analytics"),
        "summary": "Exploratory analysis, metric interpretation, and decision support.",
        "projects": ("MarketVista Dashboard", "TradeIntel 360"),
        "evidence_note": "Core DA narrative across projects and applications.",
    },
    {
        "name": "Reporting",
        "keywords": ("reporting", "report", "insights"),
        "summary": "Narrative and tabular outputs for business stakeholders.",
        "projects": ("MarketVista Dashboard", "RiskWise Planner"),
        "evidence_note": "Recruiter pack and reporting-focused roles.",
    },
    {
        "name": "KPI dashboards",
        "keywords": ("dashboard", "kpi", "power bi", "metrics"),
        "summary": "Visual monitoring of operational and commercial KPIs.",
        "projects": ("MarketVista Dashboard", "BakeOps Intelligence"),
        "evidence_note": "Dashboard-centric BI and operations roles.",
    },
    {
        "name": "ETL / data preparation",
        "keywords": ("etl", "pipeline", "data preparation", "integration"),
        "summary": "Ingestion, cleaning, and hand-off between systems.",
        "projects": ("DataBridge Market API", "TradeIntel 360", "bakeops-dbt"),
        "evidence_note": "Analytics engineering and data product angles.",
    },
    {
        "name": "dbt (portfolio)",
        "keywords": ("dbt", "data build tool"),
        "summary": (
            "Portfolio dbt modelling via bakeops-dbt; not production or cloud warehouse depth."
        ),
        "projects": ("bakeops-dbt",),
        "evidence_note": (
            "Portfolio-verified via bakeops-dbt (7 models, 26 tests, v1.0.1); "
            "not enterprise or cloud platform dbt."
        ),
    },
    {
        "name": "DuckDB (portfolio)",
        "keywords": ("duckdb",),
        "summary": (
            "Local DuckDB warehouse evidence via bakeops-dbt; not production cloud platform use."
        ),
        "projects": ("bakeops-dbt",),
        "evidence_note": "Portfolio warehouse project only; not Snowflake/BigQuery evidence.",
    },
    {
        "name": "Business operations / FX operations",
        "keywords": ("operations", "fx", "finance", "reconciliation", "ledger"),
        "summary": "Finance and operations context from prior experience and projects.",
        "projects": ("TradeIntel 360", "RiskWise Planner"),
        "evidence_note": "Finance DA targeting and recruiter evidence.",
    },
    {
        "name": "Portfolio evidence",
        "keywords": ("portfolio", "project", "case study"),
        "summary": "Documented projects that support interview and application narratives.",
        "projects": ("CareerFunnel Tracker", "BakeOps Intelligence", "MarketVista Dashboard"),
        "evidence_note": "Career Evidence OS viewer and project evidence report.",
    },
)

_ROLE_READINESS_CHECKLISTS: tuple[RoleReadinessChecklist, ...] = (
    RoleReadinessChecklist(
        role_key="da",
        role_title="Data Analyst",
        summary=(
            "Manual checklist for junior/graduate data analyst roles. Confirm "
            "evidence in applications and portfolio before applying."
        ),
        items=(
            ReadinessChecklistItem(
                "SQL and Excel artefacts",
                "Can you point to queries, tables, or spreadsheets used in real examples",
            ),
            ReadinessChecklistItem(
                "Python analysis examples",
                "Do you have a notebook, script, or project walkthrough ready to discuss",
            ),
            ReadinessChecklistItem(
                "Stakeholder reporting",
                "Can you explain one KPI story clearly without overstating scope",
            ),
            ReadinessChecklistItem(
                "Application evidence captured",
                "Are required skills and job descriptions saved on each target role",
            ),
        ),
    ),
    RoleReadinessChecklist(
        role_key="bi",
        role_title="BI Analyst",
        summary=(
            "Manual checklist for BI and reporting-heavy roles. Focus on "
            "dashboards, metric definitions, and refresh discipline."
        ),
        items=(
            ReadinessChecklistItem(
                "Dashboard examples",
                "Which portfolio project shows end-to-end metric design",
            ),
            ReadinessChecklistItem(
                "Metric definitions",
                "Can you define numerators, denominators, and caveats manually",
            ),
            ReadinessChecklistItem(
                "Data quality checks",
                "Have you documented how you validate source data before publishing",
            ),
            ReadinessChecklistItem(
                "Role text reviewed",
                (
                    "Does the posting mention Power BI, Looker, or similar tools "
                    "you can discuss honestly"
                ),
            ),
        ),
    ),
    RoleReadinessChecklist(
        role_key="ae",
        role_title="Analytics Engineer",
        summary=(
            "Manual checklist for analytics engineering and data product roles. "
            "Emphasise pipelines, modelling hand-offs, and reliability."
        ),
        items=(
            ReadinessChecklistItem(
                "Pipeline or integration story",
                "Can you walk through ingestion, transforms, and outputs from a project",
            ),
            ReadinessChecklistItem(
                "SQL + Python combination",
                "Is there evidence of both extraction logic and downstream consumption",
            ),
            ReadinessChecklistItem(
                "Documentation habit",
                "Are assumptions, dependencies, and refresh steps written down",
            ),
            ReadinessChecklistItem(
                "Stretch-role honesty",
                "Review seniority signals manually - do not rely on this page as a fit score.",
            ),
        ),
    ),
    RoleReadinessChecklist(
        role_key="de",
        role_title="Data Engineer",
        summary=(
            "Manual checklist for data engineer postings. Use only when you can "
            "support infrastructure and pipeline claims with evidence."
        ),
        items=(
            ReadinessChecklistItem(
                "Pipeline ownership",
                "Which project shows you built or maintained a repeatable data flow",
            ),
            ReadinessChecklistItem(
                "Operational awareness",
                "Can you discuss failures, retries, and monitoring without inventing tooling",
            ),
            ReadinessChecklistItem(
                "Storage and modelling basics",
                "Are source-to-target mappings documented in portfolio or notes",
            ),
            ReadinessChecklistItem(
                "Manual gap review",
                "Review LEARNING_TARGETS areas manually before claiming platform expertise.",
            ),
        ),
    ),
)

_PORTFOLIO_SKILL_MAPPINGS: tuple[PortfolioSkillMapping, ...] = (
    PortfolioSkillMapping(
        project_name="CareerFunnel Tracker",
        skills_demonstrated=(
            "Python",
            "Django",
            "Data analysis",
            "Reporting",
            "Portfolio evidence",
        ),
        manual_note=(
            "Local job-search operating system with rule-based analytics "
            "and evidence tracking."
        ),
        career_evidence_url="",
    ),
    PortfolioSkillMapping(
        project_name="BakeOps Intelligence",
        skills_demonstrated=("Python", "SQL", "Excel", "KPI dashboards", "Data analysis"),
        manual_note="Operational KPI and waste-reduction analytics narrative.",
        career_evidence_url="",
    ),
    PortfolioSkillMapping(
        project_name="MarketVista Dashboard",
        skills_demonstrated=("SQL", "Reporting", "KPI dashboards", "Data analysis"),
        manual_note="Commercial metrics and dashboard storytelling.",
        career_evidence_url="",
    ),
    PortfolioSkillMapping(
        project_name="TradeIntel 360",
        skills_demonstrated=(
            "Data analysis",
            "Reporting",
            "Business operations / FX operations",
            "ETL / data preparation",
        ),
        manual_note="Finance and markets themed analytics evidence.",
        career_evidence_url="",
    ),
    PortfolioSkillMapping(
        project_name="DataBridge Market API",
        skills_demonstrated=("Python", "ETL / data preparation", "Django"),
        manual_note="API and ingestion oriented evidence for engineering-leaning roles.",
        career_evidence_url="",
    ),
    PortfolioSkillMapping(
        project_name="bakeops-dbt",
        skills_demonstrated=(
            "dbt (portfolio)",
            "DuckDB (portfolio)",
            "SQL",
            "ETL / data preparation",
        ),
        manual_note=(
            "Portfolio analytics engineering project with 7 dbt models, 26 tests, v1.0.1; "
            "not production or cloud warehouse evidence."
        ),
        career_evidence_url="",
    ),
)


def _application_text_corpus(user) -> tuple[str, int]:
    applications = JobApplication.objects.filter(user=user).only(
        "required_skills",
        "job_description",
        "job_title",
        "notes",
    )
    chunks: list[str] = []
    count = 0
    for application in applications:
        count += 1
        chunks.extend(
            [
                application.required_skills or "",
                application.job_description or "",
                application.job_title or "",
                application.notes or "",
            ]
        )
    return "\n".join(chunks).lower(), count


def _count_keyword_matches(corpus: str, keywords: tuple[str, ...]) -> int:
    return sum(corpus.count(keyword) for keyword in keywords)


def _build_skill_evidence(corpus: str) -> tuple[SkillCategoryEvidence, ...]:
    rows: list[SkillCategoryEvidence] = []
    for entry in _SKILL_CATALOG:
        rows.append(
            SkillCategoryEvidence(
                name=entry["name"],
                evidence_summary=entry["summary"],
                portfolio_projects=tuple(entry["projects"]),
                career_evidence_note=entry["evidence_note"],
                matched_in_applications=_count_keyword_matches(corpus, entry["keywords"]),
            )
        )
    return tuple(rows)


def _build_skill_gap_prompts(
    corpus: str,
    *,
    application_count: int,
) -> tuple[SkillGapPrompt, ...]:
    prompts: list[SkillGapPrompt] = []

    if application_count == 0:
        prompts.append(
            SkillGapPrompt(
                skill_or_area="Application records",
                prompt="Log applications with required skills and job descriptions first.",
                context=(
                    "Skill Intelligence uses text you have already saved - "
                    "not live job-board scraping."
                ),
            )
        )
        return tuple(prompts)

    for entry in _SKILL_CATALOG:
        if _count_keyword_matches(corpus, entry["keywords"]) == 0:
            prompts.append(
                SkillGapPrompt(
                    skill_or_area=entry["name"],
                    prompt=(
                        f"Review {entry['name']} manually before applying to roles that require it."
                    ),
                    context=(
                        "No keyword matches found in saved application text yet. "
                        "Update records or portfolio evidence if the skill is part of your story."
                    ),
                )
            )

    for target in LEARNING_TARGETS:
        if target not in corpus:
            prompts.append(
                SkillGapPrompt(
                    skill_or_area=target,
                    prompt=(
                        f"Review {target} manually if target roles list it "
                        "as required or preferred."
                    ),
                    context=(
                        "Listed as a learning target for stretch roles - not a failed assessment."
                    ),
                )
            )

    if not prompts:
        prompts.append(
            SkillGapPrompt(
                skill_or_area="Ongoing review",
                prompt="Keep comparing new job posts to your saved skills and portfolio evidence.",
                context=(
                    "Core catalog areas appear in logged text. "
                    "Continue manual review per role."
                ),
            )
        )
    return tuple(prompts[:12])


def _skill_intelligence_manual_actions() -> tuple[ManualWorkflowLink, ...]:
    from django.urls import reverse

    return (
        ManualWorkflowLink(
            "Review applications manually",
            reverse("applications:application_list"),
        ),
        ManualWorkflowLink("Open Smart Review", reverse("job_intelligence:smart_review")),
        ManualWorkflowLink(
            "Open Career Evidence",
            reverse("dashboard:career_evidence_index"),
        ),
        ManualWorkflowLink(
            "Add application manually",
            reverse("applications:application_create"),
        ),
    )


def build_skill_intelligence_context(user) -> SkillIntelligenceContext:
    from django.urls import reverse

    corpus, application_count = _application_text_corpus(user)
    career_evidence_url = reverse("dashboard:career_evidence_index")
    portfolio_mappings = tuple(
        PortfolioSkillMapping(
            project_name=item.project_name,
            skills_demonstrated=item.skills_demonstrated,
            manual_note=item.manual_note,
            career_evidence_url=career_evidence_url,
        )
        for item in _PORTFOLIO_SKILL_MAPPINGS
    )
    return SkillIntelligenceContext(
        advisory_copy=_SKILL_INTELLIGENCE_ADVISORY,
        trust_points=_SKILL_TRUST_POINTS,
        application_count=application_count,
        skill_evidence=_build_skill_evidence(corpus),
        skill_gaps=_build_skill_gap_prompts(corpus, application_count=application_count),
        role_checklists=_ROLE_READINESS_CHECKLISTS,
        portfolio_mappings=portfolio_mappings,
        manual_actions=_skill_intelligence_manual_actions(),
    )
