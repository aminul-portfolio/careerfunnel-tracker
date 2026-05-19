"""Local evidence scanner for CareerFunnel Tracker (stdlib only)."""

from __future__ import annotations

import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

README_PATH = REPO_ROOT / "README.md"
DOCS_DIR = REPO_ROOT / "docs"
TESTS_DIR = REPO_ROOT / "tests"
TEMPLATES_DIR = REPO_ROOT / "templates"
STATIC_DIR = REPO_ROOT / "static"

REPORT_PATH = REPO_ROOT / "docs" / "career_evidence" / "01_project_evidence_report.md"

DOC_EXTENSIONS = {".md", ".rst", ".txt"}
TEST_FILE_NAMES = {"tests.py"}
TEST_FILE_PREFIX = "test_"
TEST_FILE_SUFFIX = "_test.py"
SCREENSHOT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"}
SCREENSHOT_DIR_NAMES = {"screenshots", "screenshot"}

GIT_NOT_AVAILABLE = "git not available"
GIT_COMMAND_FAILED = "git command failed"

# ASCII hyphen for GitHub-safe Markdown (avoid em/en dash encoding issues).
REPORT_TITLE = "CareerFunnel Tracker - Project Evidence Report"

MOJIBAKE_DASH_REPLACEMENTS = (
    "â€”",  # UTF-8 mojibake for em dash
    "â€“",  # UTF-8 mojibake for en dash
    "\u2014",  # em dash
    "\u2013",  # en dash
)


@dataclass
class ScanCounts:
    documentation_files: int = 0
    test_files: int = 0
    template_files: int = 0
    css_files: int = 0
    js_files: int = 0
    screenshots: int = 0


@dataclass
class ScanInventory:
    counts: ScanCounts = field(default_factory=ScanCounts)
    documentation_paths: list[str] = field(default_factory=list)
    test_paths: list[str] = field(default_factory=list)
    template_paths: list[str] = field(default_factory=list)
    css_paths: list[str] = field(default_factory=list)
    js_paths: list[str] = field(default_factory=list)
    screenshot_paths: list[str] = field(default_factory=list)
    screenshot_folders: list[str] = field(default_factory=list)
    scanned_paths: list[str] = field(default_factory=list)
    missing_scan_targets: list[str] = field(default_factory=list)


@dataclass
class GitEvidence:
    branch: str = GIT_NOT_AVAILABLE
    latest_commit: str = GIT_NOT_AVAILABLE
    status_short: str = GIT_NOT_AVAILABLE
    available: bool = False


@dataclass
class AuditResult:
    inventory: ScanInventory
    git: GitEvidence
    readme_present: bool
    readme_summary_lines: list[str]
    top_level_entries: list[str]
    missing_evidence: list[str]
    generated_at: str


def _ascii_safe_text(text: str) -> str:
    """Normalize dashes so generated Markdown renders correctly on GitHub."""
    result = text
    for sequence in MOJIBAKE_DASH_REPLACEMENTS:
        result = result.replace(sequence, "-")
    result = result.replace("â€¦", "...")  # UTF-8 mojibake for ellipsis
    result = result.replace("\u2026", "...")  # ellipsis
    return result


def _relative(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _run_git(args: list[str]) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.rstrip("\n")


def collect_git_evidence() -> GitEvidence:
    branch = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    commit = _run_git(["rev-parse", "HEAD"])
    status = _run_git(["status", "--short"])
    if branch is None and commit is None and status is None:
        return GitEvidence()
    return GitEvidence(
        branch=branch or GIT_COMMAND_FAILED,
        latest_commit=commit or GIT_COMMAND_FAILED,
        status_short=status if status is not None else "(clean or git command failed)",
        available=branch is not None and commit is not None,
    )


def _is_documentation_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in DOC_EXTENSIONS


def _is_test_file(path: Path) -> bool:
    if not path.is_file() or path.suffix.lower() != ".py":
        return False
    name = path.name
    return (
        name in TEST_FILE_NAMES
        or name.startswith(TEST_FILE_PREFIX)
        or name.endswith(TEST_FILE_SUFFIX)
    )


def _is_screenshot_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SCREENSHOT_EXTENSIONS


def _iter_files(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    if root.is_file():
        yield root
        return
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def discover_screenshot_folders() -> list[Path]:
    folders: set[Path] = set()
    if DOCS_DIR.is_dir():
        for path in DOCS_DIR.rglob("*"):
            if path.is_dir() and path.name.lower() in SCREENSHOT_DIR_NAMES:
                folders.add(path)
    return sorted(folders, key=lambda item: _relative(item))


def _record_scan_target(
    inventory: ScanInventory,
    target: Path,
    label: str,
) -> None:
    if target.exists():
        inventory.scanned_paths.append(label)
    else:
        inventory.missing_scan_targets.append(label)


def scan_repository() -> ScanInventory:
    inventory = ScanInventory()
    counts = inventory.counts

    _record_scan_target(inventory, README_PATH, _relative(README_PATH))
    if README_PATH.is_file():
        counts.documentation_files += 1
        inventory.documentation_paths.append(_relative(README_PATH))

    scan_roots: list[tuple[str, Path, str]] = [
        ("docs", DOCS_DIR, "documentation"),
        ("tests", TESTS_DIR, "test"),
        ("templates", TEMPLATES_DIR, "template"),
        ("static", STATIC_DIR, "static"),
    ]

    for label, root, kind in scan_roots:
        _record_scan_target(inventory, root, _relative(root))
        if not root.exists():
            continue
        for path in _iter_files(root):
            rel = _relative(path)
            if kind == "documentation" and _is_documentation_file(path):
                counts.documentation_files += 1
                inventory.documentation_paths.append(rel)
            elif kind == "test" and _is_test_file(path):
                counts.test_files += 1
                inventory.test_paths.append(rel)
            elif kind == "template" and path.suffix.lower() == ".html":
                counts.template_files += 1
                inventory.template_paths.append(rel)
            elif kind == "static":
                if path.suffix.lower() == ".css":
                    counts.css_files += 1
                    inventory.css_paths.append(rel)
                elif path.suffix.lower() == ".js":
                    counts.js_files += 1
                    inventory.js_paths.append(rel)

    screenshot_folders = discover_screenshot_folders()
    inventory.screenshot_folders = [_relative(folder) for folder in screenshot_folders]
    for folder in screenshot_folders:
        _record_scan_target(inventory, folder, _relative(folder))
        for path in _iter_files(folder):
            if _is_screenshot_file(path):
                counts.screenshots += 1
                inventory.screenshot_paths.append(_relative(path))

    inventory.documentation_paths.sort()
    inventory.test_paths.sort()
    inventory.template_paths.sort()
    inventory.css_paths.sort()
    inventory.js_paths.sort()
    inventory.screenshot_paths.sort()
    return inventory


def _extract_readme_summary(max_lines: int = 5) -> tuple[bool, list[str]]:
    if not README_PATH.is_file():
        return False, []
    lines: list[str] = []
    for raw_line in README_PATH.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        lines.append(stripped)
        if len(lines) >= max_lines:
            break
    return True, lines


def _list_top_level_entries() -> list[str]:
    entries: list[str] = []
    for path in sorted(REPO_ROOT.iterdir(), key=lambda item: item.name.lower()):
        suffix = "/" if path.is_dir() else ""
        entries.append(f"{path.name}{suffix}")
    return entries


def _discover_app_test_files() -> list[str]:
    apps_root = REPO_ROOT / "apps"
    if not apps_root.is_dir():
        return []
    paths: list[str] = []
    for path in sorted(apps_root.rglob("*.py")):
        if _is_test_file(path):
            paths.append(_relative(path))
    return paths


def _readme_text_lower() -> str:
    if not README_PATH.is_file():
        return ""
    return README_PATH.read_text(encoding="utf-8").lower()


def build_missing_evidence(
    inventory: ScanInventory,
    git: GitEvidence,
    readme_present: bool,
) -> list[str]:
    """Repository and product evidence gaps only (not normal in-progress Git work)."""
    missing: list[str] = []
    if not readme_present:
        missing.append("README.md is missing at repository root.")
    for target in inventory.missing_scan_targets:
        missing.append(f"Scan target missing: `{target}`")
    app_tests = _discover_app_test_files()
    if inventory.counts.test_files == 0 and not app_tests:
        missing.append("No Python test files found under `tests/` or `apps/`.")
    if not git.available:
        missing.append("Git metadata unavailable; branch and commit could not be verified.")
    if inventory.counts.screenshots == 0:
        missing.append("No screenshot image files found in discovered screenshot folders.")
    if inventory.counts.css_files == 0:
        missing.append("No CSS files found under `static/`.")
    if inventory.counts.js_files == 0:
        missing.append("No JavaScript files found under `static/`.")

    readme_lower = _readme_text_lower()
    if readme_present:
        if "not yet verified" in readme_lower or "deployment is conditional" in readme_lower:
            missing.append(
                "Live deployment is not verified; README does not claim a hosted demo URL."
            )
        if "gmail" in readme_lower and "calendar" in readme_lower:
            missing.append(
                "External integrations (Gmail, Calendar, external AI/LLM providers, scraping, "
                "auto-apply) are not implemented; README documents rule-based local logic only."
            )
        missing.append(
            "No dedicated public REST API layer is documented in README; delivery is "
            "through Django views and export workflows."
        )
    missing.append(
        "Validation command results are not captured automatically by this scanner; "
        "record outcomes from the latest terminal run after final checks."
    )
    return missing


def render_validation_evidence_section() -> list[str]:
    return [
        "## Validation Evidence",
        "",
        "The scanner does **not** execute linters, Django checks, migrations checks, or the "
        "test suite. Status below must be taken from the **latest terminal run** at review time.",
        "",
        "| Check | Status |",
        "| --- | --- |",
        "| `ruff check .` | _Not collected by scanner - verify manually_ |",
        "| `python manage.py check` | _Not collected by scanner - verify manually_ |",
        "| `python manage.py makemigrations --check --dry-run` | "
        "_Not collected by scanner - verify manually_ |",
        "| `python manage.py test` | _Not collected by scanner - verify manually_ |",
        "",
        "After final checks, paste pass/fail results and test counts into review notes. "
        "Do not assume green builds from an older report timestamp.",
        "",
    ]


def build_next_suggestions(
    inventory: ScanInventory,
    missing_evidence: list[str],
) -> list[str]:
    suggestions: list[str] = []
    if not (REPO_ROOT / "tests").is_dir() or inventory.counts.test_files == 0:
        suggestions.append(
            "Document or mirror app-level tests (`apps/*/tests.py`) in career evidence if "
            "`tests/` remains empty."
        )
    if inventory.missing_scan_targets:
        suggestions.append("Add missing scan targets or update scanner paths if layout changes.")
    critical_prefixes = ("README", "Scan target", "No Python")
    critical = [item for item in missing_evidence if item.startswith(critical_prefixes)]
    if critical:
        suggestions.append(
            "Resolve critical repository gaps listed under Missing Evidence before external review."
        )
    suggestions.append(
        "Run validation commands before review and record outcomes alongside Validation Evidence."
    )
    suggestions.append(
        "Re-run `python tools/career_evidence_audit.py` after evidence changes "
        "to refresh the report."
    )
    return suggestions


def run_audit() -> AuditResult:
    inventory = scan_repository()
    git = collect_git_evidence()
    readme_present, readme_summary_lines = _extract_readme_summary()
    missing_evidence = build_missing_evidence(inventory, git, readme_present)
    return AuditResult(
        inventory=inventory,
        git=git,
        readme_present=readme_present,
        readme_summary_lines=readme_summary_lines,
        top_level_entries=_list_top_level_entries(),
        missing_evidence=missing_evidence,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )


def _bullet_list(items: list[str], *, empty_label: str = "_None._") -> str:
    if not items:
        return f"- {empty_label}\n"
    return "".join(f"- `{item}`\n" for item in items)


def _numbered_list(items: list[str]) -> str:
    if not items:
        return "1. _None._\n"
    return "".join(f"{index}. {item}\n" for index, item in enumerate(items, start=1))


def render_report(result: AuditResult) -> str:
    inventory = result.inventory
    counts = inventory.counts
    app_tests = _discover_app_test_files()

    summary_block = (
        "_README.md not found; no project summary extracted._\n"
        if not result.readme_present
        else "".join(f"> {_ascii_safe_text(line)}\n" for line in result.readme_summary_lines)
        or "> _README present but no non-heading summary lines extracted._\n"
    )

    git_status_block = (
        "```\n"
        f"{result.git.status_short}\n"
        "```\n"
        if result.git.status_short
        else "_Git status unavailable._\n"
    )

    lines = [
        f"# {REPORT_TITLE}",
        "",
        f"_Generated by `tools/career_evidence_audit.py` on {result.generated_at}._",
        "",
        "## Project Summary",
        "",
        "The following lines are quoted from README.md (non-heading content only).",
        "",
        summary_block.rstrip(),
        "",
        "## Repository Structure",
        "",
        "Top-level entries under the repository root:",
        "",
        _bullet_list(result.top_level_entries).rstrip(),
        "",
        "## Evidence Inventory",
        "",
        "| Category | Count |",
        "| --- | ---: |",
        f"| Documentation files (README + docs/) | {counts.documentation_files} |",
        f"| Test files (`tests/` only) | {counts.test_files} |",
        f"| Template files (`templates/`) | {counts.template_files} |",
        f"| CSS files (`static/`) | {counts.css_files} |",
        f"| JavaScript files (`static/`) | {counts.js_files} |",
        f"| Screenshots (screenshot folders) | {counts.screenshots} |",
        "",
        "Scan targets checked:",
        "",
        _bullet_list(inventory.scanned_paths, empty_label="_No scan targets found._").rstrip(),
        "",
        "## Testing Evidence",
        "",
        f"- Test files under `tests/`: **{counts.test_files}**",
        "",
    ]
    if inventory.test_paths:
        lines.append("Paths:")
        lines.append("")
        lines.append(_bullet_list(inventory.test_paths).rstrip())
        lines.append("")
    if app_tests:
        lines.extend(
            [
                (
                    "Test modules under `apps/` (not counted in `tests/` total): "
                    f"**{len(app_tests)}**"
                ),
                "",
                _bullet_list(app_tests[:20]).rstrip(),
            ]
        )
        if len(app_tests) > 20:
            lines.append(f"- _... and {len(app_tests) - 20} more._")
        lines.append("")

    lines.extend(
        [
            "## Documentation Evidence",
            "",
            f"- Documentation files (README + `docs/`): **{counts.documentation_files}**",
            "",
        ]
    )
    if inventory.documentation_paths:
        lines.append("Sample paths (up to 15):")
        lines.append("")
        sample = inventory.documentation_paths[:15]
        lines.append(_bullet_list(sample).rstrip())
        if len(inventory.documentation_paths) > 15:
            lines.append(f"- _... and {len(inventory.documentation_paths) - 15} more._")
        lines.append("")

    lines.extend(
        [
            "## Frontend Asset Evidence",
            "",
            f"- HTML templates: **{counts.template_files}**",
            f"- CSS files: **{counts.css_files}**",
            f"- JavaScript files: **{counts.js_files}**",
            "",
        ]
    )
    if inventory.template_paths:
        lines.append("Template paths (up to 10):")
        lines.append("")
        lines.append(_bullet_list(inventory.template_paths[:10]).rstrip())
        if len(inventory.template_paths) > 10:
            lines.append(f"- _... and {len(inventory.template_paths) - 10} more._")
        lines.append("")

    lines.extend(
        [
            "## Screenshot Evidence",
            "",
            f"- Screenshot folders: **{len(inventory.screenshot_folders)}**",
            f"- Screenshot image files: **{counts.screenshots}**",
            "",
        ]
    )
    if inventory.screenshot_folders:
        lines.append("Folders:")
        lines.append("")
        lines.append(_bullet_list(inventory.screenshot_folders).rstrip())
        lines.append("")
    if inventory.screenshot_paths:
        lines.append("Screenshot paths (up to 15):")
        lines.append("")
        lines.append(_bullet_list(inventory.screenshot_paths[:15]).rstrip())
        if len(inventory.screenshot_paths) > 15:
            lines.append(f"- _... and {len(inventory.screenshot_paths) - 15} more._")
        lines.append("")

    lines.extend(
        [
            "## Git Status",
            "",
            f"- Current branch: `{result.git.branch}`",
            f"- Latest commit: `{result.git.latest_commit}`",
            "",
            "Short status (`git status --short`):",
            "",
            git_status_block.rstrip(),
            "",
            *render_validation_evidence_section(),
            "## Missing Evidence",
            "",
        ]
    )
    if result.missing_evidence:
        lines.append(_numbered_list(result.missing_evidence).rstrip())
    else:
        lines.append("_No missing evidence flagged by the scanner._")
    lines.extend(
        [
            "",
            "## Next Improvement Suggestions",
            "",
            _numbered_list(build_next_suggestions(inventory, result.missing_evidence)).rstrip(),
            "",
        ]
    )
    return _ascii_safe_text("\n".join(lines))


def write_report(report_text: str, output_path: Path | None = None) -> Path:
    destination = output_path or REPORT_PATH
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(_ascii_safe_text(report_text), encoding="utf-8", newline="\n")
    return destination


def main() -> int:
    result = run_audit()
    path = write_report(render_report(result))
    print(f"Wrote evidence report to {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
