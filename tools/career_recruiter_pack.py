"""Recruiter evidence pack generator (stdlib only)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

README_PATH = REPO_ROOT / "README.md"
EVIDENCE_REPORT_PATH = REPO_ROOT / "docs" / "career_evidence" / "01_project_evidence_report.md"
JOB_FIT_MATRIX_PATH = REPO_ROOT / "docs" / "career_evidence" / "02_job_fit_matrix.md"
OUTPUT_PATH = REPO_ROOT / "docs" / "career_evidence" / "03_recruiter_evidence_pack.md"

FORBIDDEN_PHRASES = (
    "enterprise-grade",
    "production-scale",
    "fully automated",
    "commercial saas",
    "real users",
    "deployed platform",
)

TARGET_ROLES_DEFAULT = (
    "Data Analyst, BI Analyst, Reporting Analyst, Analytics Engineer, "
    "Junior Data Engineer, and FinTech analytics roles"
)


@dataclass
class EvidenceSources:
    readme: str
    evidence_report: str
    job_fit_matrix: str


@dataclass
class ParsedEvidence:
    positioning_line: str
    target_roles: str
    test_count: str | None
    strong_matches: list[str]
    partial_matches: list[str]
    fit_gaps: list[str]
    matrix_limitations: list[str]
    doc_count: str | None
    template_count: str | None
    screenshot_count: str | None
    app_test_modules: str | None


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def load_sources() -> EvidenceSources:
    return EvidenceSources(
        readme=_read_text(README_PATH),
        evidence_report=_read_text(EVIDENCE_REPORT_PATH),
        job_fit_matrix=_read_text(JOB_FIT_MATRIX_PATH),
    )


def _extract_first_paragraph(readme: str) -> str:
    for line in readme.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            return stripped
    return "CareerFunnel Tracker (see README.md)."


def _extract_target_roles(readme: str) -> str:
    match = re.search(
        r"evidence for (.+?)\.",
        readme,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if match:
        roles = match.group(1).strip()
    else:
        roles = TARGET_ROLES_DEFAULT
    return _extend_target_roles(roles)


def _extend_target_roles(roles: str) -> str:
    """Ensure recruiter-facing role labels include Reporting and Insights Analyst."""
    normalized = roles.rstrip(".")
    if "reporting analyst" not in normalized.lower():
        normalized = f"{normalized}, Reporting Analyst"
    if "insights analyst" not in normalized.lower():
        if "and FinTech analytics roles" in normalized:
            normalized = normalized.replace(
                "and FinTech analytics roles",
                "and FinTech analytics roles, and Insights Analyst",
            )
        else:
            normalized = f"{normalized}, and Insights Analyst"
    return normalized


def _extract_test_count(readme: str) -> str | None:
    match = re.search(r"\*\*(\d+)\s+passing\*\*", readme)
    if match:
        return match.group(1)
    match = re.search(r"(\d+)\s+passing", readme, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _extract_section_bullets(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    collecting = False
    bullets: list[str] = []
    for line in lines:
        if line.strip() == heading:
            collecting = True
            continue
        if collecting:
            if line.startswith("## ") and line.strip() != heading:
                break
            if line.startswith("### ") and bullets:
                break
            stripped = line.strip()
            if stripped.startswith("- **"):
                label = stripped.removeprefix("- **").split("**", 1)[0].strip()
                if label:
                    bullets.append(label)
            elif stripped.startswith("- ") and not stripped.startswith("- _"):
                bullets.append(stripped.removeprefix("- ").strip())
    return bullets


def _extract_numbered_gaps(matrix: str) -> list[str]:
    lines = matrix.splitlines()
    collecting = False
    gaps: list[str] = []
    for line in lines:
        if line.strip() == "### Gaps reflected in the overall fit assessment":
            collecting = True
            continue
        if collecting:
            if line.startswith("## ") or line.startswith("### "):
                break
            match = re.match(r"^\d+\.\s+(.*)$", line.strip())
            if match:
                gaps.append(match.group(1).strip())
    return gaps


def _extract_inventory_count(report: str, label: str) -> str | None:
    pattern = rf"\|\s*{re.escape(label)}\s*\|\s*(\d+)\s*\|"
    match = re.search(pattern, report)
    return match.group(1) if match else None


def _extract_app_test_module_count(report: str) -> str | None:
    match = re.search(
        r"Test modules under `apps/` \(not counted in `tests/` total\):\s*\*\*(\d+)\*\*",
        report,
    )
    return match.group(1) if match else None


def parse_evidence(sources: EvidenceSources) -> ParsedEvidence:
    matrix = sources.job_fit_matrix
    report = sources.evidence_report
    readme = sources.readme
    return ParsedEvidence(
        positioning_line=_extract_first_paragraph(readme),
        target_roles=_extract_target_roles(readme),
        test_count=_extract_test_count(readme),
        strong_matches=_extract_section_bullets(matrix, "## Strongest Matches"),
        partial_matches=_extract_section_bullets(matrix, "## Partial Matches"),
        fit_gaps=(
            _extract_numbered_gaps(matrix)
            or _extract_section_bullets(matrix, "## Missing Evidence")
        ),
        matrix_limitations=_extract_section_bullets(matrix, "## Evidence Limitations"),
        doc_count=_extract_inventory_count(report, "Documentation files (README + docs/)"),
        template_count=_extract_inventory_count(report, "Template files (`templates/`)"),
        screenshot_count=_extract_inventory_count(report, "Screenshots (screenshot folders)"),
        app_test_modules=_extract_app_test_module_count(report),
    )


def _bullet_lines(items: list[str]) -> str:
    if not items:
        return "- _No items extracted from source evidence._"
    return "\n".join(f"- {item}" for item in items)


def _cv_bullets(parsed: ParsedEvidence) -> list[str]:
    _ = parsed  # bullets use stable wording; counts may change over time
    test_note = "automated tests documented in README"
    modules_note = "multiple app test modules in repository evidence"
    return [
        (
            "Built a Python and Django portfolio analytics application that demonstrates "
            "service-layer reporting over structured job-search records "
            "(repository evidence: `apps/`, `manage.py`, `requirements.txt`)."
        ),
        (
            "Shows evidence of funnel KPI reporting (response rate, pipeline stages, weekly "
            "trends) through `apps/metrics/` and documented metric definitions in "
            "`docs/analytics/metric_definitions.md`."
        ),
        (
            "Supports data-quality governance with readiness rules, save-time warnings, and a "
            "Data Quality Report (`templates/metrics/data_quality_report.html`; README "
            "governance callout)."
        ),
        (
            "Delivers reviewer-ready exports via workbook and CSV paths in `apps/exports/` "
            "and dashboard demo CSV tooling (`apps/exports/management/commands/"
            "export_for_dashboards.py`)."
        ),
        (
            f"Documents analytics lineage, sprint evidence, and workflow discipline with "
            f"{test_note}, {modules_note}, and `.github/workflows/django-ci.yml`."
        ),
    ]


def _linkedin_summary(parsed: ParsedEvidence) -> str:
    return (
        "CareerFunnel Tracker is a Django analytics portfolio project that turns job-search "
        "activity into explainable funnel metrics, data-quality signals, and reviewer-ready "
        "evidence. Repository evidence supports Python/Django development, KPI reporting, "
        "dashboards, exports, and governed metric documentation. This is portfolio work with "
        "honest scope limits: deployment is not verified, and external AI, Gmail/Calendar, "
        "scraping, and auto-apply are not implemented."
    )


def _interview_talking_points() -> list[tuple[str, str, str, str]]:
    return [
        (
            "Funnel metrics and KPI reporting",
            "Metrics services calculate response rate, stage breakdown, weekly trends, and "
            "related funnel views for job-search activity.",
            "Shows how operational records become explainable reporting for analyst-style review.",
            "`apps/metrics/services.py`, `templates/metrics/funnel_metrics.html`, "
            "`docs/analytics/metric_definitions.md`, README Key Analytics Modules.",
        ),
        (
            "Data-quality governance",
            "A single analytics-readiness rule propagates to save warnings and impact notes.",
            "Supports trustworthy reporting by surfacing missing fields before metrics "
            "are trusted.",
            "README Data-Quality Governance Callout; `templates/metrics/data_quality_report.html`; "
            "V2 matrix Strong match for Data quality.",
        ),
        (
            "Dashboard and reviewer walkthrough",
            "Dashboard overview and curated screenshots document a reviewer-friendly analytics UI.",
            "Helps recruiters inspect the project without a live deployment claim.",
            "`templates/dashboard/overview.html`, `docs/screenshots/curated/`, "
            "`01_project_evidence_report.md` screenshot inventory.",
        ),
        (
            "Exports for BI-style handoff",
            "Export Centre and workbook/CSV paths support evidence export for review and backup.",
            "Demonstrates practical reporting delivery beyond on-screen views only.",
            "`apps/exports/services.py`, `templates/exports/export_center.html`, "
            "README Export Centre; V2 matrix Strong match for Exports / CSV.",
        ),
        (
            "Engineering discipline without overclaiming",
            "CI workflow, local tests, and rule-based logic replace fake automation claims.",
            "Shows honest portfolio engineering aligned with junior analytics roles.",
            "`.github/workflows/django-ci.yml`, README What Is Not Claimed, "
            "V2 Partial automation row.",
        ),
    ]


def _evidence_limitations(parsed: ParsedEvidence) -> list[str]:
    _ = parsed  # grouped limitations; avoids duplicating V2 gap bullets verbatim
    return [
        (
            "**Deployment and product scope:** Live deployment is not verified; README "
            "does not claim a hosted demo URL, production users, customers, billing, or "
            "a paid subscription product."
        ),
        (
            "**Integrations and automation:** External AI/LLM, scraping, auto-apply, "
            "Gmail, and Calendar automation are not implemented (README claims control). "
            "Workflow evidence is limited to CI and management commands (V2 Partial "
            "automation)."
        ),
        (
            "**Data platform and APIs:** SQLite is documented for portfolio-scale local "
            "analytics, not a production warehouse. No dedicated public REST API layer "
            "is documented; delivery uses Django views and exports."
        ),
        (
            "**Partial evidence areas (V2):** SQL/database and automation matrix rows "
            "are Partial only. BI tooling evidence is local screenshots/workbooks unless "
            "a public URL is verified."
        ),
        (
            "**Evidence freshness:** V1/V2 inputs and this pack are point-in-time; "
            "re-run generators after material repository changes."
        ),
    ]


def _suggested_improvements() -> list[str]:
    return [
        "Verify any future deployment separately before adding a live demo URL "
        "to recruiter materials.",
        "Refresh V1/V2 evidence reports, then regenerate this pack with "
        "`python tools/career_recruiter_pack.py`.",
        "Keep recruiter wording aligned with README 'What Is Not Claimed' and V2 Missing Evidence.",
        "Add new screenshots or docs only when they exist in the repository; do not invent claims.",
    ]


def _evidence_rules() -> list[str]:
    return [
        "This pack is assembled from `README.md`, `01_project_evidence_report.md`, and "
        "`02_job_fit_matrix.md` only.",
        "Use cautious verbs: demonstrates, shows evidence of, supports, portfolio evidence.",
        "Do not claim employment, paid client delivery, production users, "
        "or a paid subscription product.",
        "No external APIs, LLM calls, or network services are used by this generator.",
    ]


def render_pack(sources: EvidenceSources, parsed: ParsedEvidence) -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    cv_bullets = _cv_bullets(parsed)
    talking_points = _interview_talking_points()
    limitations = _evidence_limitations(parsed)

    inventory_bits: list[str] = []
    if parsed.doc_count:
        inventory_bits.append(f"{parsed.doc_count} documentation files (V1 inventory)")
    if parsed.template_count:
        inventory_bits.append(f"{parsed.template_count} HTML templates (V1 inventory)")
    if parsed.screenshot_count:
        inventory_bits.append(f"{parsed.screenshot_count} screenshots (V1 inventory)")

    lines = [
        "# CareerFunnel Tracker - Recruiter Evidence Pack",
        "",
        f"_Generated by `tools/career_recruiter_pack.py` on {generated_at}._",
        "",
        "_Sources: README.md, 01_project_evidence_report.md, 02_job_fit_matrix.md._",
        "",
        "## Project Positioning Summary",
        "",
        parsed.positioning_line,
        "",
        "Deployment is conditional and not yet verified per README. This pack describes "
        "**portfolio evidence** suitable for recruiter and hiring-manager review, not a "
        "commercial product launch.",
        "",
        "## Target Roles",
        "",
        f"Repository evidence supports positioning toward: **{parsed.target_roles}**.",
        "",
        "## Core Technical Evidence",
        "",
        _bullet_lines(
            [
                "Python application code under `apps/` with dependencies in `requirements.txt` "
                "(V2 matrix: Strong).",
                "Django project structure: `manage.py`, `config/`, installed apps "
                "(V2 matrix: Strong).",
                (
                    "Automated tests: multiple passing tests documented in README; "
                    "multiple app test modules in V1 inventory."
                ),
                "CI workflow: `.github/workflows/django-ci.yml` (V2 matrix: Strong Git/GitHub).",
                (
                    "V2 strongest matches include: "
                    + ", ".join(parsed.strong_matches[:8])
                    + ("..." if len(parsed.strong_matches) > 8 else "")
                    + "."
                    if parsed.strong_matches
                    else "V2 strongest matches not extracted; regenerate `02_job_fit_matrix.md`."
                ),
            ]
        ),
        "",
        "## Business / Domain Evidence",
        "",
        _bullet_lines(
            [
                "Job-search funnel treated as an analytics domain (README Business Problem).",
                "Tracks applications, sources, CV versions, follow-ups, interviews, and notes "
                "(README What The Platform Does).",
                "Portfolio handoff and recruiter docs under `docs/evidence/` (V2 matrix: Strong "
                "stakeholder communication).",
                "Curated reviewer screenshots under `docs/screenshots/curated/` (V1 inventory).",
            ]
        ),
        "",
        "## Analytics & Reporting Evidence",
        "",
        _bullet_lines(
            [
                "Funnel Metrics, Source ROI, CV Version Performance, Rejection Pattern Analysis "
                "(README Key Analytics Modules).",
                "Application Quality and Data Quality reports (`apps/metrics/`, templates under "
                "`templates/metrics/`).",
                "Metric definitions and analytics lineage: `docs/analytics/metric_definitions.md`, "
                "`docs/analytics/analytics_lineage.md`.",
                "BI/visual evidence: local Tableau workbook and Chart.js weekly trend (README; "
                "screenshots in `docs/evidence/screenshots/`).",
            ]
        ),
        "",
        "## Workflow & Engineering Discipline",
        "",
        _bullet_lines(
            [
                "Rule-based service-layer logic; no external AI/LLM claims "
                "(README Technical Decisions).",
                "GitHub Actions CI on push/PR to `main` (V2 matrix).",
                "Management commands for demo seed and dashboard CSV export "
                "(V2 Partial automation).",
                "Five-minute reviewer path documented in README for consistent walkthroughs.",
            ]
        ),
        "",
        "## Recruiter-Friendly CV Bullets",
        "",
        "\n".join(f"{index}. {bullet}" for index, bullet in enumerate(cv_bullets, start=1)),
        "",
        "## LinkedIn Project Summary",
        "",
        _linkedin_summary(parsed),
        "",
        "## Interview Talking Points",
        "",
    ]

    for index, (title, built, matters, evidence) in enumerate(talking_points, start=1):
        lines.extend(
            [
                f"### {index}. {title}",
                "",
                f"- **What was built:** {built}",
                f"- **Why it matters:** {matters}",
                f"- **What evidence supports it:** {evidence}",
                "",
            ]
        )

    lines.extend(
        [
            "## Evidence Limitations",
            "",
            _bullet_lines(limitations),
            "",
            "## Suggested Next Improvements",
            "",
            "\n".join(
                f"{index}. {item}"
                for index, item in enumerate(_suggested_improvements(), start=1)
            ),
            "",
            "## Evidence Rules",
            "",
            _bullet_lines(_evidence_rules()),
            "",
        ]
    )

    return "\n".join(lines)


def write_pack(content: str, output_path: Path | None = None) -> Path:
    destination = output_path or OUTPUT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8", newline="\n")
    return destination


def run_pack() -> tuple[EvidenceSources, ParsedEvidence]:
    sources = load_sources()
    parsed = parse_evidence(sources)
    return sources, parsed


def main() -> int:
    missing = [
        path
        for path in (README_PATH, EVIDENCE_REPORT_PATH, JOB_FIT_MATRIX_PATH)
        if not path.is_file()
    ]
    if missing:
        names = ", ".join(str(path) for path in missing)
        raise SystemExit(f"Required evidence input missing: {names}")

    sources, parsed = run_pack()
    path = write_pack(render_pack(sources, parsed))
    print(f"Wrote recruiter evidence pack to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
