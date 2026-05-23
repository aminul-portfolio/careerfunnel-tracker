"""Structured, claim-safe evidence catalog for CV tailoring (Sprint 34A).

Advisory evidence only — no CV body generation, no external API calls.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EvidenceTier = Literal["strong", "partial", "gap_learning"]

FORBIDDEN_CLAIM_FIELD_NAMES: frozenset[str] = frozenset({
    "full_cv_text",
    "professional_summary",
    "experience_bullets",
    "cover_letter_body",
})

FORBIDDEN_CLAIM_PHRASES: tuple[str, ...] = (
    "full_cv_text",
    "professional_summary",
    "experience_bullets",
    "cover_letter_body",
    "i am excited to apply",
    "i am writing to apply",
    "dear hiring manager",
    "please find attached my cv",
    "auto-apply",
    "gmail integration",
    "calendar sync",
    "oauth",
)

GAP_LEARNING_SKILL_IDS: frozenset[str] = frozenset({
    "dbt",
    "snowflake",
    "airflow",
    "spark",
    "kafka",
    "bigquery",
    "aws_redshift",
    "redshift",
    "databricks",
})

HARD_GAP_SKILL_IDS: frozenset[str] = frozenset({
    "dbt",
    "snowflake",
    "airflow",
    "spark",
    "kafka",
    "aws_redshift",
    "sc_clearance",
    "dv_clearance",
})


@dataclass(frozen=True)
class EvidenceEntry:
    skill_id: str
    display_name: str
    tier: EvidenceTier
    claimable: bool
    evidence_summary: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProjectEvidenceEntry:
    project_id: str
    display_name: str
    role_families: tuple[str, ...]
    evidence_summary: str
    source_refs: tuple[str, ...]


@dataclass(frozen=True)
class ExperienceAngleEntry:
    angle_id: str
    label: str
    role_families: tuple[str, ...]
    evidence_summary: str


def _entry(
    skill_id: str,
    display_name: str,
    tier: EvidenceTier,
    evidence_summary: str,
    source_refs: tuple[str, ...],
) -> EvidenceEntry:
    claimable = tier != "gap_learning"
    return EvidenceEntry(
        skill_id=skill_id,
        display_name=display_name,
        tier=tier,
        claimable=claimable,
        evidence_summary=evidence_summary,
        source_refs=source_refs,
    )


_DOC = "docs/career_evidence/cv_project_bullet_bank.md"
_PORTFOLIO = "docs/career_evidence/portfolio_project_index.md"
_S31A = "docs/evidence/sprint_31a_cv_evidence_source_audit.md"

EVIDENCE_ENTRIES: dict[str, EvidenceEntry] = {
    # Strong evidence
    "python": _entry(
        "python",
        "Python",
        "strong",
        "Python portfolio projects and data-processing workflows.",
        (_DOC, _PORTFOLIO),
    ),
    "django": _entry(
        "django",
        "Django",
        "strong",
        (
            "Django-based analytics platforms including BakeOps, MarketVista, "
            "RiskWise, and CareerFunnel."
        ),
        (_DOC, _PORTFOLIO),
    ),
    "excel": _entry(
        "excel",
        "Excel",
        "strong",
        "Advanced Excel, cashflow platform, scorecards, formulas, and reporting.",
        (_DOC, _S31A),
    ),
    "reporting": _entry(
        "reporting",
        "Reporting",
        "strong",
        "Operational reporting, KPI tracking, and monthly performance reporting.",
        (_DOC, _S31A),
    ),
    "kpi_dashboards": _entry(
        "kpi_dashboards",
        "KPI dashboards",
        "strong",
        "KPI modelling in BakeOps Intelligence and operational reporting roles.",
        (_DOC, _PORTFOLIO),
    ),
    "finance": _entry(
        "finance",
        "Finance operations",
        "strong",
        "Money transfer, FX, remittance, reconciliations, and finance operations.",
        (_DOC, _S31A),
    ),
    "reconciliation": _entry(
        "reconciliation",
        "Reconciliation",
        "strong",
        "FX/remittance operations and audit-ready cashflow records.",
        (_DOC, _S31A),
    ),
    "pandas": _entry(
        "pandas",
        "pandas",
        "strong",
        "Python/pandas analytics project work.",
        (_DOC, _PORTFOLIO),
    ),
    "stakeholder": _entry(
        "stakeholder",
        "Stakeholder reporting",
        "strong",
        (
            "Agent training, operational support, and business-facing "
            "reporting experience."
        ),
        (_DOC, _S31A),
    ),
    # Partial evidence
    "sql": _entry(
        "sql",
        "SQL",
        "partial",
        (
            "Database-backed Django projects and dashboard-ready data models; "
            "strengthen explicit SQL examples if needed."
        ),
        (_DOC, _PORTFOLIO),
    ),
    "etl": _entry(
        "etl",
        "ETL-style workflows",
        "partial",
        "DataBridge Market API and analytics ETL-style workflows.",
        (_DOC, _PORTFOLIO),
    ),
    "api_development": _entry(
        "api_development",
        "API development",
        "partial",
        "Django API-style JSON endpoints and market-data ingestion projects.",
        (_DOC, _PORTFOLIO),
    ),
    "data_visualisation": _entry(
        "data_visualisation",
        "Data visualisation",
        "partial",
        "MarketVista, BakeOps, and CareerFunnel dashboard pages.",
        (_DOC, _PORTFOLIO),
    ),
    "power_bi": _entry(
        "power_bi",
        "Power BI",
        "partial",
        "Dashboard evidence via portfolio projects; not a primary production stack claim.",
        (_DOC,),
    ),
    "tableau": _entry(
        "tableau",
        "Tableau",
        "partial",
        "Dashboard evidence via portfolio projects; strengthen only with explicit examples.",
        (_DOC,),
    ),
    # Gap / learning targets — never claimable
    "dbt": _entry(
        "dbt",
        "dbt",
        "gap_learning",
        "Learning target; portfolio shows ETL-style patterns only — not production dbt depth.",
        (_S31A,),
    ),
    "snowflake": _entry(
        "snowflake",
        "Snowflake",
        "gap_learning",
        "Learning target; not production-proven in repository evidence.",
        (_S31A,),
    ),
    "airflow": _entry(
        "airflow",
        "Airflow",
        "gap_learning",
        "Learning target; do not claim orchestration production experience.",
        (_S31A,),
    ),
    "spark": _entry(
        "spark",
        "Spark",
        "gap_learning",
        "Learning target; not evidenced as production Spark experience.",
        (_S31A,),
    ),
    "kafka": _entry(
        "kafka",
        "Kafka",
        "gap_learning",
        "Learning target; not evidenced as production Kafka experience.",
        (_S31A,),
    ),
    "bigquery": _entry(
        "bigquery",
        "BigQuery",
        "gap_learning",
        "Learning target; cloud warehouse exposure is stretch-only.",
        (_S31A,),
    ),
    "aws_redshift": _entry(
        "aws_redshift",
        "AWS Redshift",
        "gap_learning",
        "Learning target; not production-proven in repository evidence.",
        (_S31A,),
    ),
    "redshift": _entry(
        "redshift",
        "Redshift",
        "gap_learning",
        "Learning target; not production-proven in repository evidence.",
        (_S31A,),
    ),
    "databricks": _entry(
        "databricks",
        "Databricks",
        "gap_learning",
        "Learning target; not production-proven in repository evidence.",
        (_S31A,),
    ),
    "sc_clearance": _entry(
        "sc_clearance",
        "SC clearance",
        "gap_learning",
        "Hard gap — not held; treat as blocker unless role is flexible.",
        (_S31A,),
    ),
    "dv_clearance": _entry(
        "dv_clearance",
        "DV clearance",
        "gap_learning",
        "Hard gap — not held; treat as blocker unless role is flexible.",
        (_S31A,),
    ),
}

PROJECT_ENTRIES: dict[str, ProjectEvidenceEntry] = {
    "careerfunnel": ProjectEvidenceEntry(
        project_id="careerfunnel",
        display_name="CareerFunnel Tracker",
        role_families=("Data Analyst", "BI / Reporting Analytics"),
        evidence_summary=(
            "Django job-search analytics platform with governed metrics and manual workflows."
        ),
        source_refs=(_PORTFOLIO, _DOC),
    ),
    "bakeops": ProjectEvidenceEntry(
        project_id="bakeops",
        display_name="BakeOps Intelligence",
        role_families=("BI / Reporting Analytics", "Data Analyst"),
        evidence_summary="KPI and operational reporting dashboard project.",
        source_refs=(_PORTFOLIO, _DOC),
    ),
    "marketvista": ProjectEvidenceEntry(
        project_id="marketvista",
        display_name="MarketVista Dashboard",
        role_families=("BI / Reporting Analytics", "Finance / FinTech Analytics"),
        evidence_summary="Market and performance dashboard evidence.",
        source_refs=(_PORTFOLIO, _DOC),
    ),
    "databridge": ProjectEvidenceEntry(
        project_id="databridge",
        display_name="DataBridge Market API",
        role_families=("Analytics Engineering / Data Product Stretch",),
        evidence_summary="API and market-data ingestion portfolio evidence.",
        source_refs=(_PORTFOLIO, _DOC),
    ),
    "tradeintel": ProjectEvidenceEntry(
        project_id="tradeintel",
        display_name="TradeIntel 360",
        role_families=("Finance / FinTech Analytics",),
        evidence_summary="Finance and market analytics portfolio project.",
        source_refs=(_PORTFOLIO, _DOC),
    ),
    "riskwise": ProjectEvidenceEntry(
        project_id="riskwise",
        display_name="RiskWise Planner",
        role_families=("Finance / FinTech Analytics",),
        evidence_summary="Risk and planning analytics portfolio project.",
        source_refs=(_PORTFOLIO, _DOC),
    ),
}

_DISPLAY_NAME_TO_PROJECT_ID: dict[str, str] = {
    entry.display_name: entry.project_id for entry in PROJECT_ENTRIES.values()
}

EXPERIENCE_ANGLE_ENTRIES: dict[str, ExperienceAngleEntry] = {
    "finance_reconciliation": ExperienceAngleEntry(
        angle_id="finance_reconciliation",
        label="FX, remittance, finance operations, and reconciliation discipline",
        role_families=("Finance / FinTech Analytics",),
        evidence_summary="Documented finance/operations background from portfolio wording packs.",
    ),
    "operational_kpi": ExperienceAngleEntry(
        angle_id="operational_kpi",
        label="Operational reporting and KPI tracking",
        role_families=(
            "Finance / FinTech Analytics",
            "BI / Reporting Analytics",
            "Data Analyst",
        ),
        evidence_summary="KPI and monthly reporting angles backed by BakeOps and operations work.",
    ),
    "dashboard_modelling": ExperienceAngleEntry(
        angle_id="dashboard_modelling",
        label="Dashboard-ready data modelling",
        role_families=("BI / Reporting Analytics", "Data Analyst"),
        evidence_summary="Dashboard and data-model evidence from MarketVista and CareerFunnel.",
    ),
    "python_delivery": ExperienceAngleEntry(
        angle_id="python_delivery",
        label="Python/Django analytics project delivery",
        role_families=("Data Analyst", "Analytics Engineering / Data Product Stretch"),
        evidence_summary="Portfolio projects built with Python and Django.",
    ),
    "pipeline_stretch": ExperienceAngleEntry(
        angle_id="pipeline_stretch",
        label="Pipeline/API-style portfolio evidence with honest tool-gap boundaries",
        role_families=("Analytics Engineering / Data Product Stretch",),
        evidence_summary=(
            "DataBridge and API evidence without claiming production dbt/Airflow depth."
        ),
    ),
}

_SKILL_ALIASES: dict[str, str] = {
    "api": "api_development",
    "kpi": "kpi_dashboards",
    "dashboard": "data_visualisation",
    "visualisation": "data_visualisation",
    "visualization": "data_visualisation",
}


def _normalise_skill_id(raw: str) -> str:
    return raw.strip().lower().replace(" ", "_").replace("-", "_")


def _resolve_skill_id(raw: str) -> str | None:
    skill_id = _normalise_skill_id(raw)
    if skill_id in EVIDENCE_ENTRIES:
        return skill_id
    if skill_id in _SKILL_ALIASES:
        return _SKILL_ALIASES[skill_id]
    return None


def get_evidence_entry(skill_id: str) -> EvidenceEntry | None:
    resolved = _resolve_skill_id(skill_id)
    if resolved is None:
        return None
    return EVIDENCE_ENTRIES[resolved]


def tier_for_skill(skill_id: str) -> EvidenceTier | None:
    entry = get_evidence_entry(skill_id)
    if entry is None:
        return None
    return entry.tier


def is_claimable_skill(skill_id: str) -> bool:
    entry = get_evidence_entry(skill_id)
    if entry is None:
        return False
    return entry.claimable and entry.tier != "gap_learning"


def _filter_skills_by_tier(skill_ids: list[str], tier: EvidenceTier) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in skill_ids:
        resolved = _resolve_skill_id(raw)
        if resolved is None or resolved in seen:
            continue
        entry = EVIDENCE_ENTRIES[resolved]
        if entry.tier != tier:
            continue
        seen.add(resolved)
        result.append(resolved)
    return result


def filter_claimable_for_matched(skill_ids: list[str]) -> list[str]:
    """Return strong-tier claimable skills only; exclude partial, gap, and unknown."""
    seen: set[str] = set()
    result: list[str] = []
    for raw in skill_ids:
        resolved = _resolve_skill_id(raw)
        if resolved is None or resolved in seen:
            continue
        entry = EVIDENCE_ENTRIES[resolved]
        if not entry.claimable or entry.tier != "strong":
            continue
        seen.add(resolved)
        result.append(resolved)
    return result


def filter_partial_skills(skill_ids: list[str]) -> list[str]:
    return _filter_skills_by_tier(skill_ids, "partial")


def filter_gap_learning_skills(skill_ids: list[str]) -> list[str]:
    return _filter_skills_by_tier(skill_ids, "gap_learning")


def validate_project_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for raw in names:
        name = raw.strip()
        if not name:
            continue
        project_id = _DISPLAY_NAME_TO_PROJECT_ID.get(name)
        if project_id is None:
            continue
        entry = PROJECT_ENTRIES[project_id]
        if entry.display_name in seen:
            continue
        seen.add(entry.display_name)
        result.append(entry.display_name)
    return result


def contains_forbidden_claim_field(value: str) -> bool:
    normalised = value.strip().lower()
    if not normalised:
        return False
    if normalised in FORBIDDEN_CLAIM_FIELD_NAMES:
        return True
    return any(phrase in normalised for phrase in FORBIDDEN_CLAIM_PHRASES)
