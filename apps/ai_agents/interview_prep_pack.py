from __future__ import annotations

from dataclasses import dataclass

from apps.ai_agents.evidence_bank import validate_project_names
from apps.applications.models import JobApplication
from apps.applications.services import (
    build_application_cv_version_display,
    display_application_cv_version_for_application,
)

LOCKED_CV = "Aminul_Islam_Data_Analyst_CV"


@dataclass(frozen=True)
class InterviewProjectEvidence:
    name: str
    interview_purpose: str
    best_technical_evidence: str
    business_value: str
    question_types: tuple[str, ...]


@dataclass(frozen=True)
class InterviewTechnicalTopic:
    topic: str
    why_it_matters: str
    project_evidence: str
    revision_focus: str


@dataclass(frozen=True)
class InterviewQuestionGroup:
    group_name: str
    questions: tuple[str, ...]


@dataclass(frozen=True)
class InterviewStarAnswer:
    title: str
    situation: str
    task: str
    action: str
    result: str
    project_evidence: str
    best_question_fit: str


@dataclass(frozen=True)
class InterviewEvidenceStory:
    project_name: str
    context: str
    problem: str
    tools_used: str
    output: str
    business_value: str
    sixty_second_pitch: str


@dataclass(frozen=True)
class InterviewEmployerQuestionGroup:
    theme: str
    questions: tuple[str, ...]


@dataclass(frozen=True)
class InterviewPrepPack:
    profile_angle: str
    projects_to_use: tuple[str, ...]
    project_evidence: tuple[InterviewProjectEvidence, ...]
    technical_topics: tuple[InterviewTechnicalTopic, ...]
    likely_questions: tuple[InterviewQuestionGroup, ...]
    star_examples: tuple[InterviewStarAnswer, ...]
    evidence_stories: tuple[InterviewEvidenceStory, ...]
    questions_to_ask: tuple[InterviewEmployerQuestionGroup, ...]
    preparation_tasks: tuple[str, ...]
    cv_version_label: str
    preparation_status: str


_PROJECT_PROFILES: dict[str, dict[str, object]] = {
    "BakeOps Intelligence": {
        "interview_purpose": (
            "KPI reporting, data quality, dashboard-ready exports, and metric governance."
        ),
        "best_technical_evidence": (
            "KPI definitions, operational reporting tables, export-ready outputs, "
            "and reconciliation-style data checks."
        ),
        "business_value": (
            "Shows how operational metrics support margin, waste, and product decisions."
        ),
        "question_types": (
            "dashboards",
            "business insight",
            "data quality",
            "stakeholder reporting",
        ),
        "story": {
            "context": "Operational analytics project focused on bakery KPI visibility.",
            "problem": (
                "Operational data was spread across spreadsheets with inconsistent KPI "
                "definitions."
            ),
            "tools": "Python, Django, Excel-style reporting logic, KPI modelling.",
            "output": "Dashboard-ready KPI views and governed metric definitions.",
            "business_value": (
                "Improved visibility into product performance, waste, and margin signals."
            ),
            "pitch": (
                "BakeOps Intelligence turned scattered operational data into governed KPI "
                "reports so stakeholders could review performance with consistent definitions."
            ),
        },
        "topic_evidence": {
            "Excel lookups/pivots": "BakeOps KPI tables and export-ready reporting views.",
            "KPI definitions": "BakeOps metric governance and operational KPI modelling.",
            "Dashboard interpretation": "BakeOps dashboard-ready KPI outputs.",
            "Data quality checks": "BakeOps reconciliation-style validation before reporting.",
            "Stakeholder reporting": "BakeOps business-facing KPI summaries.",
            "Power BI/dashboard concepts": "BakeOps dashboard structure and KPI layout logic.",
        },
    },
    "CareerFunnel Tracker": {
        "interview_purpose": (
            "Structured records, workflow analytics, source-performance reporting, "
            "skill-gap tracking, Application Document Pack workflow, and test discipline."
        ),
        "best_technical_evidence": (
            "Django models, reporting views, validation discipline, and manual workflow "
            "boundaries."
        ),
        "business_value": (
            "Demonstrates structured analytics delivery, evidence governance, and "
            "repeatable reporting logic."
        ),
        "question_types": (
            "Django systems",
            "workflow design",
            "reporting logic",
            "validation discipline",
        ),
        "story": {
            "context": "Personal job-search analytics platform with governed manual workflows.",
            "problem": (
                "Application data was hard to track consistently across sources, CV "
                "versions, and follow-up stages."
            ),
            "tools": "Python, Django, SQLite, rule-based analytics, test-driven validation.",
            "output": (
                "Structured application records, funnel metrics, and document-pack "
                "readiness views."
            ),
            "business_value": (
                "Shows end-to-end workflow design, reporting discipline, and honest "
                "claim boundaries."
            ),
            "pitch": (
                "CareerFunnel Tracker organises application data into structured records "
                "and reporting views so I can review funnel performance and document "
                "readiness with validation discipline."
            ),
        },
        "topic_evidence": {
            "SQL filtering and joins": "CareerFunnel Tracker application and reporting records.",
            "Python/pandas data cleaning": "CareerFunnel Tracker data normalisation patterns.",
            "Data quality checks": "CareerFunnel Tracker validation and claim-safety checks.",
            "Stakeholder reporting": "CareerFunnel funnel and source-performance reports.",
        },
    },
    "MarketVista Dashboard": {
        "interview_purpose": (
            "Market data monitoring, analyst visibility, watchlists, and alert-style signals."
        ),
        "best_technical_evidence": (
            "Dashboard monitoring views, market signal interpretation, and analyst-facing "
            "visibility patterns."
        ),
        "business_value": (
            "Shows market monitoring, visual interpretation, and decision-support "
            "dashboard design."
        ),
        "question_types": (
            "dashboards",
            "API-style data handling",
            "monitoring",
            "visual interpretation",
        ),
        "story": {
            "context": "Market monitoring dashboard for analyst visibility.",
            "problem": (
                "Market signals were difficult to monitor consistently without a structured "
                "dashboard view."
            ),
            "tools": "Python, Django, dashboard components, watchlist-style monitoring logic.",
            "output": "Analyst-facing dashboard with watchlists and alert-style signals.",
            "business_value": (
                "Improved visibility into market movements and monitoring priorities."
            ),
            "pitch": (
                "MarketVista Dashboard gives analysts a structured view of market signals "
                "and watchlists so they can monitor changes without losing context."
            ),
        },
        "topic_evidence": {
            "Dashboard interpretation": "MarketVista monitoring views and watchlist signals.",
            "Power BI/dashboard concepts": "MarketVista dashboard layout and signal design.",
            "API ingestion": "MarketVista API-style market data handling patterns.",
        },
    },
    "TradeIntel 360": {
        "interview_purpose": (
            "Finance and market analytics with portfolio-style monitoring evidence."
        ),
        "best_technical_evidence": (
            "Finance analytics views, market interpretation, and reporting discipline."
        ),
        "business_value": (
            "Supports finance and FinTech analytics roles with market-focused evidence."
        ),
        "question_types": (
            "finance analytics",
            "market monitoring",
            "reporting discipline",
        ),
        "story": {
            "context": "Finance and market analytics portfolio project.",
            "problem": (
                "Market and finance signals needed a structured analytics view for "
                "interpretation."
            ),
            "tools": "Python, Django, finance analytics logic, reporting outputs.",
            "output": "Finance-focused analytics dashboard and monitoring views.",
            "business_value": (
                "Demonstrates finance analytics thinking with honest portfolio boundaries."
            ),
            "pitch": (
                "TradeIntel 360 organises finance and market signals into structured "
                "analytics views for clearer monitoring and interpretation."
            ),
        },
        "topic_evidence": {
            "Dashboard interpretation": "TradeIntel finance and market monitoring views.",
            "KPI definitions": "TradeIntel finance metric framing.",
        },
    },
    "RiskWise Planner": {
        "interview_purpose": (
            "Risk planning analytics and structured decision-support reporting."
        ),
        "best_technical_evidence": (
            "Risk framing, planning views, and structured reporting outputs."
        ),
        "business_value": (
            "Useful for finance and risk-aware analytics conversations."
        ),
        "question_types": (
            "risk framing",
            "planning analytics",
            "structured reporting",
        ),
        "story": {
            "context": "Risk and planning analytics portfolio project.",
            "problem": (
                "Planning decisions needed clearer risk-aware reporting structure."
            ),
            "tools": "Python, Django, planning analytics logic.",
            "output": "Risk-aware planning dashboard and reporting views.",
            "business_value": (
                "Shows structured thinking for risk and planning analytics roles."
            ),
            "pitch": (
                "RiskWise Planner structures risk and planning signals into reporting "
                "views that support clearer decision conversations."
            ),
        },
        "topic_evidence": {
            "KPI definitions": "RiskWise planning and risk metric framing.",
            "Stakeholder reporting": "RiskWise planning summaries for decision support.",
        },
    },
    "DataBridge Market API": {
        "interview_purpose": (
            "API ingestion, market-data handling, and pipeline-style portfolio evidence."
        ),
        "best_technical_evidence": (
            "API ingestion patterns, data handoff logic, and honest pipeline boundaries."
        ),
        "business_value": (
            "Supports analytics-engineering stretch conversations without overstating "
            "production pipeline depth."
        ),
        "question_types": (
            "API ingestion",
            "ETL workflow explanation",
            "data handoff",
        ),
        "story": {
            "context": "Portfolio project focused on API-style market data ingestion.",
            "problem": (
                "Market data needed a structured ingestion and handoff pattern for "
                "downstream reporting."
            ),
            "tools": "Python, Django, API ingestion logic, structured data handoff.",
            "output": "Market-data ingestion workflow with reporting-ready outputs.",
            "business_value": (
                "Demonstrates pipeline thinking with honest tool-gap boundaries."
            ),
            "pitch": (
                "DataBridge Market API shows how I structure API ingestion and data "
                "handoff for reporting-ready outputs without claiming production ETL depth."
            ),
        },
        "topic_evidence": {
            "API ingestion": "DataBridge API ingestion and handoff workflow.",
            "ETL workflow explanation": "DataBridge ingestion-to-reporting handoff pattern.",
        },
    },
}

_BASE_TECHNICAL_TOPICS: tuple[tuple[str, str, str], ...] = (
    (
        "Excel lookups/pivots",
        "Many analyst roles still rely on Excel for reporting and reconciliation.",
        "Lookups, pivots, formulas, and structured tables.",
    ),
    (
        "SQL filtering and joins",
        "Analyst roles often require extracting and combining data from multiple sources.",
        "Filtering, grouping, joins, and aggregations.",
    ),
    (
        "Python/pandas data cleaning",
        "Portfolio projects show practical data cleaning and export discipline.",
        "Cleaning, grouping, exporting, and basic transformations.",
    ),
    (
        "KPI definitions",
        "Reporting quality depends on clear, consistent metric definitions.",
        "Metric naming, calculation logic, and stakeholder alignment.",
    ),
    (
        "Dashboard interpretation",
        "Roles often expect you to explain what a dashboard shows and why it matters.",
        "Signal reading, trend interpretation, and business context.",
    ),
    (
        "Data quality checks",
        "Messy or incomplete data is common in real reporting work.",
        "Validation checks, reconciliation discipline, and exception handling.",
    ),
    (
        "Stakeholder reporting",
        "Analyst work must translate data into decisions non-technical teams can use.",
        "Plain-language summaries, context, and next-step recommendations.",
    ),
)


def _application_text(application: JobApplication) -> str:
    return " ".join(
        [
            application.job_title or "",
            application.required_skills or "",
            application.job_description or "",
            application.notes or "",
        ]
    ).lower()


def select_application_project_evidence(application: JobApplication) -> tuple[str, ...]:
    text = _application_text(application)
    if any(word in text for word in ["finance", "risk", "trading", "market", "banking"]):
        projects = ["TradeIntel 360", "RiskWise Planner", "MarketVista Dashboard"]
    elif any(
        word in text
        for word in ["operations", "kpi", "margin", "waste", "product performance"]
    ):
        projects = [
            "BakeOps Intelligence",
            "CareerFunnel Tracker",
            "MarketVista Dashboard",
        ]
    elif any(word in text for word in ["etl", "api", "pipeline", "integration"]):
        projects = ["DataBridge Market API", "MarketVista Dashboard", "TradeIntel 360"]
    else:
        projects = [
            "BakeOps Intelligence",
            "MarketVista Dashboard",
            "CareerFunnel Tracker",
        ]
    validated = validate_project_names(projects)
    return tuple(validated or projects)


def _project_profile(name: str) -> dict[str, object]:
    return _PROJECT_PROFILES.get(name, {})


def _build_project_evidence(projects: tuple[str, ...]) -> tuple[InterviewProjectEvidence, ...]:
    cards: list[InterviewProjectEvidence] = []
    for name in projects:
        profile = _project_profile(name)
        cards.append(
            InterviewProjectEvidence(
                name=name,
                interview_purpose=str(profile.get("interview_purpose", "Portfolio evidence.")),
                best_technical_evidence=str(
                    profile.get("best_technical_evidence", "Structured analytics evidence.")
                ),
                business_value=str(
                    profile.get("business_value", "Supports practical analytics conversations.")
                ),
                question_types=tuple(profile.get("question_types", ("project walkthrough",))),
            )
        )
    return tuple(cards)


def _pick_topic_evidence(topic: str, projects: tuple[str, ...]) -> str:
    for project in projects:
        topic_map = _project_profile(project).get("topic_evidence", {})
        if isinstance(topic_map, dict) and topic in topic_map:
            return str(topic_map[topic])
    return f"{projects[0]} reporting and analytics outputs."


def _build_technical_topics(
    application: JobApplication,
    projects: tuple[str, ...],
) -> tuple[InterviewTechnicalTopic, ...]:
    text = _application_text(application)
    topics: list[InterviewTechnicalTopic] = []
    for topic, why_default, revision in _BASE_TECHNICAL_TOPICS:
        topics.append(
            InterviewTechnicalTopic(
                topic=topic,
                why_it_matters=why_default,
                project_evidence=_pick_topic_evidence(topic, projects),
                revision_focus=revision,
            )
        )
    if "power bi" in text:
        topics.append(
            InterviewTechnicalTopic(
                topic="Power BI/dashboard concepts",
                why_it_matters=(
                    "This role mentions dashboard tooling; be ready to discuss concepts "
                    "even if Power BI depth is still developing."
                ),
                project_evidence=_pick_topic_evidence("Power BI/dashboard concepts", projects),
                revision_focus="Dashboard layout, KPI cards, filters, and drill-down logic.",
            )
        )
    if "api" in text or "etl" in text:
        topics.append(
            InterviewTechnicalTopic(
                topic="API ingestion",
                why_it_matters=(
                    "Pipeline or integration signals suggest ingestion workflow questions."
                ),
                project_evidence=_pick_topic_evidence("API ingestion", projects),
                revision_focus="Ingestion steps, data handoff, and validation boundaries.",
            )
        )
        topics.append(
            InterviewTechnicalTopic(
                topic="ETL workflow explanation",
                why_it_matters="You may be asked to explain how data moves from source to report.",
                project_evidence=_pick_topic_evidence("ETL workflow explanation", projects),
                revision_focus="Source, transform, validate, and reporting-ready output.",
            )
        )
    return tuple(topics)


def _build_likely_questions(
    application: JobApplication,
    projects: tuple[str, ...],
) -> tuple[InterviewQuestionGroup, ...]:
    company = application.company_name or "this company"
    role = application.job_title or "this role"
    project_questions = [
        "Walk me through one analytics project from problem to output.",
        f"Which project best demonstrates your reporting ability for {role}?",
    ]
    if "BakeOps Intelligence" in projects:
        project_questions.append(
            "What was the most important insight from BakeOps Intelligence?"
        )
    if "CareerFunnel Tracker" in projects:
        project_questions.append(
            "How did CareerFunnel Tracker help you organise application data?"
        )
    if "MarketVista Dashboard" in projects:
        project_questions.append(
            "How would you explain MarketVista Dashboard to a non-technical stakeholder?"
        )
    if "TradeIntel 360" in projects:
        project_questions.append(
            "How does TradeIntel 360 demonstrate finance analytics thinking?"
        )
    if "DataBridge Market API" in projects:
        project_questions.append(
            "How would you explain your DataBridge ingestion workflow?"
        )
    if "RiskWise Planner" in projects:
        project_questions.append(
            "What planning or risk signals does RiskWise Planner help communicate?"
        )

    return (
        InterviewQuestionGroup(
            group_name="Motivation / Profile",
            questions=(
                "Tell me about yourself and your move into data analytics.",
                f"Why are you interested in this {role} role?",
                f"Why are you interested in {company}?",
            ),
        ),
        InterviewQuestionGroup(
            group_name="Technical",
            questions=(
                "How have you used Excel, SQL, Python, or dashboards in practical work?",
                "How would you check data quality before reporting?",
                "How would you explain a KPI to a non-technical stakeholder?",
            ),
        ),
        InterviewQuestionGroup(
            group_name="Project Evidence",
            questions=tuple(project_questions),
        ),
        InterviewQuestionGroup(
            group_name="Behavioural",
            questions=(
                "Tell me about a time you handled incomplete or messy data.",
                "Tell me about a time you explained something complex to a non-technical person.",
                "Tell me about a time you improved a process.",
            ),
        ),
    )


def _primary_project(projects: tuple[str, ...]) -> str:
    return projects[0] if projects else "CareerFunnel Tracker"


def _secondary_project(projects: tuple[str, ...]) -> str:
    if len(projects) > 1:
        return projects[1]
    return _primary_project(projects)


def _build_star_answers(projects: tuple[str, ...]) -> tuple[InterviewStarAnswer, ...]:
    primary = _primary_project(projects)
    secondary = _secondary_project(projects)
    return (
        InterviewStarAnswer(
            title="Improving a reporting or reconciliation process",
            situation=(
                "In finance/operations work, reporting inputs arrived from multiple "
                "sources with inconsistent formats."
            ),
            task=(
                "Improve reporting accuracy and make reconciliation checks easier to repeat."
            ),
            action=(
                "Standardised lookup steps, documented validation checks, and organised "
                "reporting tables before sharing outputs."
            ),
            result=(
                "Reporting became easier to review, exceptions were clearer, and "
                "stakeholders could trust the numbers more consistently."
            ),
            project_evidence="Acaelus / FX operations background",
            best_question_fit="Tell me about a time you improved a process.",
        ),
        InterviewStarAnswer(
            title="Handling accuracy under pressure in finance/operations",
            situation=(
                "A time-sensitive finance/operations task required accurate figures under "
                "deadline pressure."
            ),
            task="Deliver accurate outputs without skipping validation checks.",
            action=(
                "Prioritised reconciliation checks, flagged exceptions early, and "
                "communicated assumptions clearly before final submission."
            ),
            result=(
                "Delivered on time with documented checks and fewer downstream corrections."
            ),
            project_evidence="Acaelus / FX operations background",
            best_question_fit="Tell me about a time you handled incomplete or messy data.",
        ),
        InterviewStarAnswer(
            title="Building or improving a data/project workflow",
            situation=(
                f"{secondary} needed a clearer workflow from raw inputs to reporting-ready "
                "outputs."
            ),
            task="Design a structured workflow that supports repeatable reporting.",
            action=(
                "Mapped data stages, added validation boundaries, and documented manual "
                "review steps before outputs were shared."
            ),
            result=(
                "Created a clearer workflow that made reporting and review easier to repeat."
            ),
            project_evidence=secondary,
            best_question_fit="Walk me through one analytics project from problem to output.",
        ),
        InterviewStarAnswer(
            title="Learning a technical skill and applying it to a project",
            situation=(
                f"I needed to apply Python/Django analytics skills in a practical project "
                f"({primary})."
            ),
            task="Turn a reporting problem into a working analytics deliverable.",
            action=(
                "Learned the required tooling through structured practice, built the core "
                "workflow, and validated outputs against clear requirements."
            ),
            result=(
                "Delivered a portfolio project that demonstrates practical analytics "
                "delivery with honest boundaries."
            ),
            project_evidence=primary,
            best_question_fit=(
                "How have you used Excel, SQL, Python, or dashboards in practical work?"
            ),
        ),
        InterviewStarAnswer(
            title="Explaining complex information to a non-technical person",
            situation=(
                "A stakeholder needed to understand a reporting output without technical "
                "detail overload."
            ),
            task="Explain the insight clearly and show why it mattered for decisions.",
            action=(
                "Used plain language, focused on business impact, and walked through one "
                "concrete example rather than tool jargon."
            ),
            result=(
                "The stakeholder understood the recommendation and could act on the insight."
            ),
            project_evidence=primary,
            best_question_fit=(
                "Tell me about a time you explained something complex to a non-technical person."
            ),
        ),
        InterviewStarAnswer(
            title="Solving a data quality or incomplete-data issue",
            situation=(
                f"While building {primary}, some inputs were incomplete or inconsistent."
            ),
            task="Prevent weak data from reaching reporting outputs.",
            action=(
                "Added validation checks, documented missing fields, and separated "
                "confirmed records from provisional ones."
            ),
            result=(
                "Reporting outputs stayed evidence-based and exceptions were visible "
                "before sharing."
            ),
            project_evidence=primary,
            best_question_fit="How would you check data quality before reporting?",
        ),
    )


def _build_evidence_stories(projects: tuple[str, ...]) -> tuple[InterviewEvidenceStory, ...]:
    stories: list[InterviewEvidenceStory] = []
    for name in projects:
        profile = _project_profile(name)
        story = profile.get("story", {})
        if not isinstance(story, dict):
            story = {}
        stories.append(
            InterviewEvidenceStory(
                project_name=name,
                context=str(story.get("context", f"{name} portfolio project.")),
                problem=str(
                    story.get("problem", "A reporting or analytics problem needed structure.")
                ),
                tools_used=str(story.get("tools", "Python, Django, and reporting logic.")),
                output=str(story.get("output", "Structured analytics outputs.")),
                business_value=str(
                    story.get("business_value", "Supports practical analytics conversations.")
                ),
                sixty_second_pitch=str(
                    story.get(
                        "pitch",
                        (
                            f"{name} demonstrates structured analytics delivery with "
                            "evidence-based boundaries."
                        ),
                    )
                ),
            )
        )
    return tuple(stories)


def _build_employer_questions() -> tuple[InterviewEmployerQuestionGroup, ...]:
    return (
        InterviewEmployerQuestionGroup(
            theme="Reporting and Metrics",
            questions=(
                "What are the most important reports or KPIs this role supports?",
                "Which metrics does the team review most often?",
            ),
        ),
        InterviewEmployerQuestionGroup(
            theme="Tools and Workflow",
            questions=(
                "What tools does the team use for analysis and reporting?",
                "How does the team manage data quality and unclear requirements?",
            ),
        ),
        InterviewEmployerQuestionGroup(
            theme="Team and Development",
            questions=(
                "What would success look like in the first three months?",
                "What support is available for someone developing further in analytics?",
            ),
        ),
        InterviewEmployerQuestionGroup(
            theme="Role Expectations",
            questions=(
                "What types of analysis would this role handle weekly?",
                "Who are the main stakeholders for this role?",
            ),
        ),
    )


def _build_checklist(
    application: JobApplication,
    projects: tuple[str, ...],
) -> tuple[str, ...]:
    tasks = [
        "Prepare a 60-second profile answer.",
    ]
    for project in projects:
        tasks.append(f"Prepare one strong {project} explanation.")
    tasks.extend(
        [
            "Review Excel basics: lookups, pivots, formulas.",
            "Review SQL basics: SELECT, WHERE, JOIN, GROUP BY.",
            "Review Python/pandas basics: cleaning, grouping, exporting.",
            "Review KPI definitions and dashboard interpretation.",
            "Prepare two STAR stories from work experience.",
            "Prepare two STAR stories from portfolio projects.",
            "Prepare three questions to ask the interviewer.",
            (
                "Confirm CV version and cover letter used for this application "
                f"({display_application_cv_version_for_application(application)})."
            ),
            f"Review {application.company_name or 'the company'} and "
            f"{application.job_title or 'the role'} before interview.",
        ]
    )
    return tuple(tasks)


def _build_profile_angle(
    application: JobApplication,
    projects: tuple[str, ...],
) -> str:
    project_phrase = ", ".join(projects[:3])
    role = application.job_title or "this analytics role"
    return (
        "Position yourself as a finance and operations professional moving into data "
        "analytics, with practical evidence in KPI reporting, reconciliation discipline, "
        "dashboard-ready outputs, and Python/Django analytics projects. "
        f"For {role}, emphasise Excel/SQL/Python reporting discipline, structured workflow "
        f"thinking, and evidence from {project_phrase}. "
        f"Reference {LOCKED_CV} only as the internal baseline CV; lead with project and "
        "work evidence rather than tool claims you cannot prove."
    )


def build_interview_prep_pack(application: JobApplication) -> InterviewPrepPack:
    projects = select_application_project_evidence(application)
    cv_display = build_application_cv_version_display(application)
    return InterviewPrepPack(
        profile_angle=_build_profile_angle(application, projects),
        projects_to_use=projects,
        project_evidence=_build_project_evidence(projects),
        technical_topics=_build_technical_topics(application, projects),
        likely_questions=_build_likely_questions(application, projects),
        star_examples=_build_star_answers(projects),
        evidence_stories=_build_evidence_stories(projects),
        questions_to_ask=_build_employer_questions(),
        preparation_tasks=_build_checklist(application, projects),
        cv_version_label=cv_display.professional_basename,
        preparation_status="Advisory preparation guide - manual review required",
    )


def generate_interview_prep(application: JobApplication) -> InterviewPrepPack:
    return build_interview_prep_pack(application)
