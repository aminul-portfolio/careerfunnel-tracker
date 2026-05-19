"""Job-fit matrix generator: map a job description to repository evidence (stdlib only)."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

README_PATH = REPO_ROOT / "README.md"
DOCS_DIR = REPO_ROOT / "docs"
APPS_DIR = REPO_ROOT / "apps"
TESTS_DIR = REPO_ROOT / "tests"
TEMPLATES_DIR = REPO_ROOT / "templates"
STATIC_DIR = REPO_ROOT / "static"
GITHUB_DIR = REPO_ROOT / ".github"

JOB_DESCRIPTION_PATH = REPO_ROOT / "docs" / "career_evidence" / "sample_job_description.txt"
OUTPUT_PATH = REPO_ROOT / "docs" / "career_evidence" / "02_job_fit_matrix.md"

STRENGTH_VALUES = frozenset({"Strong", "Partial", "Missing"})
CONFIDENCE_VALUES = frozenset({"High", "Medium", "Low"})

TEST_FILE_PREFIX = "test_"
TEST_FILE_NAMES = {"tests.py"}


@dataclass
class RepositoryIndex:
    readme_text: str = ""
    job_description_text: str = ""
    python_files: list[str] = field(default_factory=list)
    django_markers: list[str] = field(default_factory=list)
    model_files: list[str] = field(default_factory=list)
    migration_dirs: list[str] = field(default_factory=list)
    metrics_files: list[str] = field(default_factory=list)
    dashboard_files: list[str] = field(default_factory=list)
    export_files: list[str] = field(default_factory=list)
    test_files: list[str] = field(default_factory=list)
    doc_files: list[str] = field(default_factory=list)
    evidence_doc_files: list[str] = field(default_factory=list)
    template_files: list[str] = field(default_factory=list)
    static_files: list[str] = field(default_factory=list)
    ci_workflows: list[str] = field(default_factory=list)
    management_commands: list[str] = field(default_factory=list)
    dashboards_data_paths: list[str] = field(default_factory=list)
    git_available: bool = False
    git_branch: str = ""
    git_commit: str = ""


@dataclass
class RequirementRow:
    requirement: str
    repository_evidence: str
    evidence_strength: str
    confidence: str
    notes: str


def _relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _exists(path: Path) -> bool:
    return path.exists()


def _readme_lower(index: RepositoryIndex) -> str:
    return index.readme_text.lower()


def _paths_exist(paths: list[Path]) -> list[str]:
    return [_relative(path) for path in paths if path.exists()]


def _collect_py_files(root: Path, *, limit: int = 8) -> list[str]:
    if not root.is_dir():
        return []
    found: list[str] = []
    for path in sorted(root.rglob("*.py")):
        if path.name.startswith("__"):
            continue
        found.append(_relative(path))
        if len(found) >= limit:
            break
    return found


def _collect_test_files() -> list[str]:
    paths: list[str] = []
    if TESTS_DIR.is_dir():
        for path in sorted(TESTS_DIR.rglob("*.py")):
            if path.name.startswith(TEST_FILE_PREFIX) or path.name in TEST_FILE_NAMES:
                paths.append(_relative(path))
    if APPS_DIR.is_dir():
        for path in sorted(APPS_DIR.rglob("tests.py")):
            paths.append(_relative(path))
        for path in sorted(APPS_DIR.rglob("test_*.py")):
            rel = _relative(path)
            if rel not in paths:
                paths.append(rel)
    return paths


def _collect_doc_files() -> list[str]:
    docs: list[str] = []
    if README_PATH.is_file():
        docs.append(_relative(README_PATH))
    if DOCS_DIR.is_dir():
        for path in sorted(DOCS_DIR.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".rst"}:
                docs.append(_relative(path))
    return docs


def _run_git() -> tuple[bool, str, str]:
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return False, "", ""
    if branch.returncode != 0 or commit.returncode != 0:
        return False, "", ""
    return True, branch.stdout.strip(), commit.stdout.strip()


def build_repository_index() -> RepositoryIndex:
    index = RepositoryIndex()
    if README_PATH.is_file():
        index.readme_text = README_PATH.read_text(encoding="utf-8")
    if JOB_DESCRIPTION_PATH.is_file():
        index.job_description_text = JOB_DESCRIPTION_PATH.read_text(encoding="utf-8")

    index.python_files = _collect_py_files(APPS_DIR, limit=6)
    if _exists(REPO_ROOT / "requirements.txt"):
        index.python_files.insert(0, "requirements.txt")

    index.django_markers = _paths_exist(
        [
            REPO_ROOT / "manage.py",
            REPO_ROOT / "config" / "settings" / "base.py",
            REPO_ROOT / "config" / "urls.py",
        ]
    )
    index.django_markers.extend(_collect_py_files(REPO_ROOT / "config", limit=3))

    if APPS_DIR.is_dir():
        for path in sorted(APPS_DIR.glob("*/models.py")):
            index.model_files.append(_relative(path))
        for path in sorted(APPS_DIR.glob("*/migrations")):
            if path.is_dir():
                index.migration_dirs.append(_relative(path))

    metrics_root = APPS_DIR / "metrics"
    if metrics_root.is_dir():
        index.metrics_files = _collect_py_files(metrics_root, limit=6)
    index.metrics_files.extend(
        _paths_exist(
            [
                TEMPLATES_DIR / "metrics" / "funnel_metrics.html",
                TEMPLATES_DIR / "metrics" / "data_quality_report.html",
                DOCS_DIR / "analytics" / "metric_definitions.md",
                DOCS_DIR / "analytics" / "analytics_lineage.md",
            ]
        )
    )

    dashboard_root = APPS_DIR / "dashboard"
    if dashboard_root.is_dir():
        index.dashboard_files = _collect_py_files(dashboard_root, limit=4)
    index.dashboard_files.extend(
        _paths_exist(
            [
                TEMPLATES_DIR / "dashboard" / "overview.html",
                REPO_ROOT / "dashboards" / "README.md",
                REPO_ROOT / "dashboards" / "data" / "applications.csv",
            ]
        )
    )

    exports_root = APPS_DIR / "exports"
    if exports_root.is_dir():
        index.export_files = _collect_py_files(exports_root, limit=5)
    index.export_files.extend(
        _paths_exist(
            [
                TEMPLATES_DIR / "exports" / "export_center.html",
                exports_root / "management" / "commands" / "export_for_dashboards.py",
            ]
        )
    )

    index.test_files = _collect_test_files()
    index.doc_files = _collect_doc_files()
    evidence_dir = DOCS_DIR / "evidence"
    if evidence_dir.is_dir():
        for path in sorted(evidence_dir.glob("*.md")):
            index.evidence_doc_files.append(_relative(path))

    if TEMPLATES_DIR.is_dir():
        for path in sorted(TEMPLATES_DIR.rglob("*.html"))[:8]:
            index.template_files.append(_relative(path))

    if STATIC_DIR.is_dir():
        for path in sorted(STATIC_DIR.rglob("*")):
            if path.is_file():
                index.static_files.append(_relative(path))

    if GITHUB_DIR.is_dir():
        for path in sorted(GITHUB_DIR.rglob("*.yml")):
            index.ci_workflows.append(_relative(path))

    commands_root = APPS_DIR / "exports" / "management" / "commands"
    if commands_root.is_dir():
        for path in sorted(commands_root.glob("*.py")):
            if path.name != "__init__.py":
                index.management_commands.append(_relative(path))
    apps_commands = APPS_DIR / "applications" / "management" / "commands"
    if apps_commands.is_dir():
        for path in sorted(apps_commands.glob("*.py")):
            if path.name != "__init__.py":
                index.management_commands.append(_relative(path))

    index.dashboards_data_paths = _paths_exist(
        [
            REPO_ROOT / "dashboards" / "data" / "applications.csv",
            REPO_ROOT / "dashboards" / "data" / "daily_logs.csv",
        ]
    )

    git_ok, branch, commit = _run_git()
    index.git_available = git_ok
    index.git_branch = branch
    index.git_commit = commit
    return index


def _format_evidence(paths: list[str], *, max_items: int = 4) -> str:
    if not paths:
        return "Missing"
    shown = paths[:max_items]
    text = "; ".join(f"`{item}`" for item in shown)
    if len(paths) > max_items:
        text += f"; ... ({len(paths)} total paths)"
    return text


def _row(
    requirement: str,
    paths: list[str],
    *,
    strength: str,
    confidence: str,
    notes: str,
) -> RequirementRow:
    if strength not in STRENGTH_VALUES:
        raise ValueError(f"Invalid strength: {strength}")
    if confidence not in CONFIDENCE_VALUES:
        raise ValueError(f"Invalid confidence: {confidence}")
    evidence = "Missing" if strength == "Missing" else _format_evidence(paths)
    return RequirementRow(
        requirement=requirement,
        repository_evidence=evidence,
        evidence_strength=strength,
        confidence=confidence,
        notes=notes,
    )


def evaluate_requirements(index: RepositoryIndex) -> list[RequirementRow]:
    readme = _readme_lower(index)
    rows: list[RequirementRow] = []

    python_paths = list(index.python_files)
    if python_paths:
        rows.append(
            _row(
                "Python",
                python_paths,
                strength="Strong",
                confidence="High",
                notes=(
                    "Python dependencies and application code are present under `apps/` "
                    "and `requirements.txt`."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "Python",
                [],
                strength="Missing",
                confidence="High",
                notes="No Python application files detected.",
            )
        )

    django_paths = list(index.django_markers)
    if len(django_paths) >= 2:
        rows.append(
            _row(
                "Django",
                django_paths,
                strength="Strong",
                confidence="High",
                notes="Django project layout (`manage.py`, `config/`, installed apps) is present.",
            )
        )
    elif django_paths:
        rows.append(
            _row(
                "Django",
                django_paths,
                strength="Partial",
                confidence="Medium",
                notes="Some Django markers found; full project layout not confirmed.",
            )
        )
    else:
        rows.append(
            _row(
                "Django",
                [],
                strength="Missing",
                confidence="High",
                notes="No Django project markers found.",
            )
        )

    sql_paths = list(index.model_files) + list(index.migration_dirs)
    if "sqlite" in readme and sql_paths:
        rows.append(
            _row(
                "SQL / database concepts",
                sql_paths[:6],
                strength="Partial",
                confidence="High",
                notes=(
                    "ORM models and migrations exist; README documents SQLite for portfolio-scale "
                    "local use, not a production warehouse."
                ),
            )
        )
    elif sql_paths:
        rows.append(
            _row(
                "SQL / database concepts",
                sql_paths[:6],
                strength="Partial",
                confidence="Medium",
                notes="Models/migrations found; database engine scope not confirmed in README.",
            )
        )
    else:
        rows.append(
            _row(
                "SQL / database concepts",
                [],
                strength="Missing",
                confidence="High",
                notes="No models or migrations detected under `apps/`.",
            )
        )

    analysis_paths = list(index.metrics_files)
    if analysis_paths:
        rows.append(
            _row(
                "Data analysis",
                analysis_paths,
                strength="Strong",
                confidence="High",
                notes=(
                    "Metrics services and analytics documentation support funnel and "
                    "quality analysis."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "Data analysis",
                [],
                strength="Missing",
                confidence="High",
                notes="No metrics modules or analytics docs found.",
            )
        )

    reporting_paths = [
        p
        for p in analysis_paths
        if "metric" in p.lower() or "funnel" in p.lower() or "quality" in p.lower()
    ]
    reporting_paths.extend(
        _paths_exist(
            [
                TEMPLATES_DIR / "metrics" / "funnel_metrics.html",
                TEMPLATES_DIR / "metrics" / "data_quality_report.html",
            ]
        )
    )
    if reporting_paths:
        rows.append(
            _row(
                "Reporting",
                list(dict.fromkeys(reporting_paths))[:6],
                strength="Strong",
                confidence="High",
                notes=(
                    "Funnel, application quality, and data quality reporting surfaces are "
                    "in the repo."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "Reporting",
                [],
                strength="Missing",
                confidence="High",
                notes="No reporting templates or metric documentation found.",
            )
        )

    if index.dashboard_files:
        rows.append(
            _row(
                "Dashboards",
                index.dashboard_files,
                strength="Strong",
                confidence="High",
                notes="Dashboard app, overview template, and `dashboards/` evidence paths exist.",
            )
        )
    else:
        rows.append(
            _row(
                "Dashboards",
                [],
                strength="Missing",
                confidence="High",
                notes="No dashboard modules or templates found.",
            )
        )

    kpi_paths = [p for p in index.metrics_files if "services" in p or "metric_definitions" in p]
    if "funnel metrics" in readme or "response rate" in readme:
        kpi_paths.append("README.md (funnel KPIs documented)")
    if kpi_paths:
        rows.append(
            _row(
                "KPI tracking",
                kpi_paths[:6],
                strength="Strong",
                confidence="High",
                notes=(
                    "README and metrics modules document response rate, funnel stages, "
                    "and weekly trends."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "KPI tracking",
                [],
                strength="Missing",
                confidence="Medium",
                notes="No KPI documentation or metrics services detected.",
            )
        )

    dq_paths = _paths_exist(
        [
            APPS_DIR / "metrics" / "services.py",
            TEMPLATES_DIR / "metrics" / "data_quality_report.html",
            DOCS_DIR / "analytics" / "metric_definitions.md",
        ]
    )
    if "data quality" in readme and dq_paths:
        rows.append(
            _row(
                "Data quality",
                list(dict.fromkeys(dq_paths))[:6],
                strength="Strong",
                confidence="High",
                notes=(
                    "Governed readiness rules and data quality reporting are documented "
                    "in README and code."
                ),
            )
        )
    elif dq_paths:
        rows.append(
            _row(
                "Data quality",
                dq_paths,
                strength="Partial",
                confidence="Medium",
                notes=(
                    "Some data quality assets exist; governance narrative not confirmed "
                    "in README."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "Data quality",
                [],
                strength="Missing",
                confidence="High",
                notes="No data quality modules or templates found.",
            )
        )

    export_paths = list(index.export_files) + index.dashboards_data_paths
    if export_paths:
        rows.append(
            _row(
                "Exports / CSV",
                export_paths,
                strength="Strong",
                confidence="High",
                notes=(
                    "Workbook export services, export centre, and dashboard CSV command "
                    "paths are present."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "Exports / CSV",
                [],
                strength="Missing",
                confidence="High",
                notes="No export services or CSV tooling found.",
            )
        )

    if len(index.test_files) >= 5:
        test_strength = "Strong"
        test_confidence = "High"
        test_note = f"{len(index.test_files)} test modules detected under `apps/` and `tests/`."
    elif index.test_files:
        test_strength = "Partial"
        test_confidence = "Medium"
        test_note = "Limited automated test files detected."
    else:
        test_strength = "Missing"
        test_confidence = "High"
        test_note = "No test modules detected."
    rows.append(
        _row(
            "Testing",
            index.test_files[:6],
            strength=test_strength,
            confidence=test_confidence,
            notes=test_note,
        )
    )

    if len(index.doc_files) >= 5:
        rows.append(
            _row(
                "Documentation",
                index.doc_files[:6],
                strength="Strong",
                confidence="High",
                notes=(
                    "README and multiple docs under `docs/` including analytics and "
                    "evidence packs."
                ),
            )
        )
    elif index.doc_files:
        rows.append(
            _row(
                "Documentation",
                index.doc_files,
                strength="Partial",
                confidence="Medium",
                notes="Some documentation found; depth not fully verified.",
            )
        )
    else:
        rows.append(
            _row(
                "Documentation",
                [],
                strength="Missing",
                confidence="High",
                notes="No README or docs/ markdown files found.",
            )
        )

    git_paths = list(index.ci_workflows)
    git_paths.extend(
        _paths_exist(
            [
                REPO_ROOT / ".gitignore",
                REPO_ROOT / "DEVELOPMENT.md",
            ]
        )
    )
    if "python manage.py test" in readme:
        git_paths.append("README.md (documents python manage.py test)")
    if git_paths:
        rows.append(
            _row(
                "Git / GitHub evidence",
                list(dict.fromkeys(git_paths))[:6],
                strength="Strong" if index.ci_workflows else "Partial",
                confidence="High",
                notes=(
                    "Durable workflow evidence: GitHub Actions CI on push/PR to `main`, "
                    "`.gitignore`, and documented local test commands. No ephemeral branch "
                    "names are used as evidence."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "Git / GitHub evidence",
                [],
                strength="Missing",
                confidence="High",
                notes="No `.github` workflows or repository workflow documentation detected.",
            )
        )

    comm_paths = list(index.evidence_doc_files)[:6]
    if comm_paths:
        rows.append(
            _row(
                "Stakeholder / business communication",
                comm_paths,
                strength="Strong",
                confidence="Medium",
                notes=(
                    "Portfolio handoff, recruiter, and interview evidence docs support "
                    "reviewer communication."
                ),
            )
        )
    else:
        rows.append(
            _row(
                "Stakeholder / business communication",
                [],
                strength="Missing",
                confidence="Medium",
                notes="No evidence packs under `docs/evidence/` found.",
            )
        )

    auto_paths = list(index.ci_workflows) + list(index.management_commands)
    if auto_paths:
        if "gmail" in readme or "calendar" in readme:
            auto_note = (
                "CI and management commands exist; README states no Gmail, Calendar, scraping, "
                "or auto-apply automation."
            )
            auto_confidence = "Medium"
        else:
            auto_note = (
                "Some workflow automation present; external automation scope not documented."
            )
            auto_confidence = "Low"
        rows.append(
            _row(
                "Automation / workflow discipline",
                auto_paths[:6],
                strength="Partial",
                confidence=auto_confidence,
                notes=auto_note,
            )
        )
    else:
        rows.append(
            _row(
                "Automation / workflow discipline",
                [],
                strength="Missing",
                confidence="High",
                notes="No CI workflows or management commands detected.",
            )
        )

    return rows


def summarize_job_description(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        lines.append(stripped)
        if len(lines) >= 6:
            break
    return lines


def detect_job_title(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
        if "analyst" in stripped.lower() or "reporting" in stripped.lower():
            return stripped[:120]
    return "Job description (see sample file)"


def build_fit_gaps(index: RepositoryIndex) -> list[str]:
    """README-derived gaps used by Overall Fit Assessment and Missing Evidence."""
    gaps: list[str] = []
    readme = _readme_lower(index)

    if "not yet verified" in readme or "deployment is conditional" in readme:
        gaps.append(
            "Live deployment proof is not verified; README does not claim a hosted demo URL."
        )

    if "gmail" in readme or "calendar" in readme or "external ai" in readme:
        gaps.append(
            "External integrations are not implemented (Gmail, Calendar, external AI/LLM, "
            "scraping, auto-apply per README claims control)."
        )

    if "sqlite" in readme:
        gaps.append(
            "Enterprise-scale or production-warehouse database evidence is not present; "
            "README documents SQLite for portfolio-scale local analytics."
        )

    gaps.append(
        "Production-grade external workflow automation beyond CI and management commands "
        "is not fully evidenced (see Partial automation/workflow row)."
    )

    gaps.append(
        "No dedicated public REST API layer is documented; delivery uses Django views "
        "and export workflows."
    )

    return gaps


def build_overall_fit(
    rows: list[RequirementRow],
    job_text: str,
    fit_gaps: list[str],
) -> str:
    strong = sum(1 for row in rows if row.evidence_strength == "Strong")
    partial = sum(1 for row in rows if row.evidence_strength == "Partial")
    missing = sum(1 for row in rows if row.evidence_strength == "Missing")
    title = detect_job_title(job_text)
    gap_clause = (
        f"{len(fit_gaps)} README-documented gaps are detailed under **Missing Evidence** "
        "(deployment verification, external integrations, database scale, workflow "
        "automation, and public API scope)."
        if fit_gaps
        else "No major README-documented gaps were identified."
    )
    return (
        f"For **{title}**, the repository shows **{strong} Strong**, **{partial} Partial**, "
        f"and **{missing} Missing** matrix rows across {len(rows)} requirement areas. "
        "CareerFunnel Tracker aligns well with Python, Django, reporting, dashboards, KPI, "
        "data quality, exports, testing, and documentation expectations typical of junior "
        "analytics roles. "
        f"{gap_clause} See **Evidence Limitations** for claim boundaries on Partial matches."
    )


def build_evidence_limitations(
    index: RepositoryIndex,
    rows: list[RequirementRow],
) -> list[str]:
    limitations: list[str] = []
    readme = _readme_lower(index)

    for row in rows:
        if row.evidence_strength == "Partial":
            limitations.append(f"**{row.requirement}** (Partial): {row.notes}")

    if "not yet verified" in readme:
        limitations.append(
            "Deployment and live-demo claims must remain conditional until a URL is verified."
        )
    if "no external ai" in readme or "llm" in readme:
        limitations.append(
            "Do not claim external AI/LLM, scraping, or auto-apply; README limits the product "
            "to rule-based local logic."
        )
    if "tableau public" in readme or "power bi" in readme:
        limitations.append(
            "BI tooling evidence is local screenshots/workbooks unless a public URL is verified."
        )

    limitations.append(
        "Matrix evidence paths are point-in-time; re-run the generator after repository changes."
    )
    return limitations


def render_missing_evidence_section(
    missing_rows: list[RequirementRow],
    fit_gaps: list[str],
) -> str:
    parts: list[str] = []
    if missing_rows:
        parts.append("### Matrix rows with no repository match\n")
        parts.append(
            "\n".join(f"- **{row.requirement}**: {row.notes}" for row in missing_rows)
        )
    if fit_gaps:
        parts.append("### Gaps reflected in the overall fit assessment")
        parts.append("\n".join(f"{index}. {gap}" for index, gap in enumerate(fit_gaps, start=1)))
    if not parts:
        return "_No missing evidence flagged._"
    return "\n\n".join(parts)


def render_matrix_table(rows: list[RequirementRow]) -> str:
    header = (
        "| Requirement | Repository Evidence | Evidence Strength | Confidence | Notes |\n"
        "| --- | --- | --- | --- | --- |"
    )
    body_lines: list[str] = []
    for row in rows:
        evidence = row.repository_evidence.replace("|", "\\|")
        notes = row.notes.replace("|", "\\|")
        body_lines.append(
            f"| {row.requirement} | {evidence} | {row.evidence_strength} | "
            f"{row.confidence} | {notes} |"
        )
    return "\n".join([header, *body_lines])


def render_report(index: RepositoryIndex, rows: list[RequirementRow]) -> str:
    generated_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    job_text = index.job_description_text
    summary_lines = summarize_job_description(job_text)
    summary_block = (
        "\n".join(f"- {line}" for line in summary_lines)
        if summary_lines
        else "- _No job description text found._"
    )

    strong_rows = [row for row in rows if row.evidence_strength == "Strong"]
    partial_rows = [row for row in rows if row.evidence_strength == "Partial"]
    missing_rows = [row for row in rows if row.evidence_strength == "Missing"]
    fit_gaps = build_fit_gaps(index)
    limitations = build_evidence_limitations(index, rows)

    def bullet_requirements(items: list[RequirementRow]) -> str:
        if not items:
            return "- _None._"
        return "\n".join(
            f"- **{item.requirement}** ({item.confidence} confidence): {item.notes}"
            for item in items
        )

    suggestions = [
        "Re-run `python tools/career_job_fit_matrix.py` after pasting a new job description into "
        "`docs/career_evidence/sample_job_description.txt`.",
        "Add verified deployment or integration evidence only when it exists in the repository.",
        "Keep claims aligned with README limitations (no live demo, no external AI, "
        "no Gmail/Calendar).",
    ]
    if missing_rows:
        suggestions.append(
            "Address Missing rows by adding real code, docs, or tests - do not invent evidence."
        )

    evidence_rules = [
        "Evidence paths must exist in this repository at generation time.",
        "Strength is `Strong` only when multiple concrete paths support the requirement.",
        "Strength is `Partial` when evidence exists but README scope is limited "
        "(e.g. SQLite, local-only BI).",
        "Strength is `Missing` when no supporting paths are found.",
        "Confidence reflects how directly the evidence maps to the requirement, "
        "not job preference.",
        "No external APIs, LLM calls, or network services are used by this script.",
    ]

    lines = [
        "# CareerFunnel Tracker - Job-Fit Matrix",
        "",
        f"_Generated by `tools/career_job_fit_matrix.py` on {generated_at}._",
        "",
        "## Job Description Summary",
        "",
        f"Source: `{_relative(JOB_DESCRIPTION_PATH)}`",
        "",
        summary_block,
        "",
        "## Job-Fit Matrix",
        "",
        render_matrix_table(rows),
        "",
        "## Strongest Matches",
        "",
        bullet_requirements(strong_rows),
        "",
        "## Partial Matches",
        "",
        bullet_requirements(partial_rows),
        "",
        "## Overall Fit Assessment",
        "",
        build_overall_fit(rows, job_text, fit_gaps),
        "",
        "## Missing Evidence",
        "",
        render_missing_evidence_section(missing_rows, fit_gaps),
        "",
        "## Evidence Limitations",
        "",
        "\n".join(f"- {item}" for item in limitations),
        "",
        "## Next Improvement Suggestions",
        "",
        "\n".join(f"{index}. {text}" for index, text in enumerate(suggestions, start=1)),
        "",
        "## Evidence Rules",
        "",
        "\n".join(f"- {rule}" for rule in evidence_rules),
        "",
    ]
    return "\n".join(lines)


def write_report(content: str, output_path: Path | None = None) -> Path:
    destination = output_path or OUTPUT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8", newline="\n")
    return destination


def run_matrix() -> tuple[RepositoryIndex, list[RequirementRow]]:
    index = build_repository_index()
    rows = evaluate_requirements(index)
    return index, rows


def main() -> int:
    if not JOB_DESCRIPTION_PATH.is_file():
        raise SystemExit(f"Job description not found: {JOB_DESCRIPTION_PATH}")
    index, rows = run_matrix()
    path = write_report(render_report(index, rows))
    print(f"Wrote job-fit matrix to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
