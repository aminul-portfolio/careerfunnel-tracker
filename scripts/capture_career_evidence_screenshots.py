"""Capture reviewer-ready Career Evidence dashboard screenshots (Playwright)."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "screenshots" / "career_evidence"

DEFAULT_BASE_URL = "http://127.0.0.1:8000/dashboard"
DEFAULT_SITE_URL = "http://127.0.0.1:8000"
LOGIN_PATH = "/accounts/login/"

VIEWPORT_WIDTH = 1440
VIEWPORT_HEIGHT = 1200

PAGE_LOAD_TIMEOUT_MS = 30_000
CONTENT_SELECTOR = ".career-evidence-page"

USERNAME_ENV = "CAREER_EVIDENCE_SCREENSHOT_USERNAME"
PASSWORD_ENV = "CAREER_EVIDENCE_SCREENSHOT_PASSWORD"
BASE_URL_ENV = "CAREER_EVIDENCE_SCREENSHOT_BASE_URL"
SITE_URL_ENV = "CAREER_EVIDENCE_SCREENSHOT_SITE_URL"


@dataclass(frozen=True)
class PageCapture:
    path: str
    filename: str
    label: str


PAGE_CAPTURES: tuple[PageCapture, ...] = (
    PageCapture(
        path="/career-evidence/",
        filename="career_evidence_overview.png",
        label="Career Evidence overview",
    ),
    PageCapture(
        path="/career-evidence/project-evidence/",
        filename="project_evidence_report.png",
        label="Project evidence report",
    ),
    PageCapture(
        path="/career-evidence/job-fit-matrix/",
        filename="job_fit_matrix.png",
        label="Job-fit matrix",
    ),
    PageCapture(
        path="/career-evidence/recruiter-pack/",
        filename="recruiter_pack.png",
        label="Recruiter pack",
    ),
)

EXPECTED_FILENAMES: frozenset[str] = frozenset(capture.filename for capture in PAGE_CAPTURES)
REQUIRED_PATHS: frozenset[str] = frozenset(capture.path for capture in PAGE_CAPTURES)


def resolve_base_url() -> str:
    return os.environ.get(BASE_URL_ENV, DEFAULT_BASE_URL).rstrip("/")


def resolve_site_url() -> str:
    return os.environ.get(SITE_URL_ENV, DEFAULT_SITE_URL).rstrip("/")


def build_page_url(base_url: str, path: str) -> str:
    normalized_path = path if path.startswith("/") else f"/{path}"
    return urljoin(f"{base_url.rstrip('/')}/", normalized_path.lstrip("/"))


def build_login_url(site_url: str) -> str:
    return build_page_url(site_url, LOGIN_PATH)


def read_credentials() -> tuple[str, str]:
    username = os.environ.get(USERNAME_ENV, "").strip()
    password = os.environ.get(PASSWORD_ENV, "")
    if not username or not password:
        raise RuntimeError(
            "Missing screenshot credentials. Set development-only environment variables:\n"
            f"  {USERNAME_ENV}\n"
            f"  {PASSWORD_ENV}\n"
            "Use any local dev account (for example after `python manage.py seed_demo_data`)."
        )
    return username, password


def ensure_output_dir(output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def authenticate(page, site_url: str, username: str, password: str) -> None:
    login_url = build_login_url(site_url)
    page.goto(login_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
    if "/accounts/login/" in page.url:
        raise RuntimeError(
            "Login did not succeed. Check local credentials and that the dev server is running."
        )


def capture_page(page, capture: PageCapture, base_url: str, output_dir: Path) -> Path:
    target_url = build_page_url(base_url, capture.path)
    page.goto(target_url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    page.wait_for_selector(CONTENT_SELECTOR, timeout=PAGE_LOAD_TIMEOUT_MS)
    page.wait_for_load_state("networkidle", timeout=PAGE_LOAD_TIMEOUT_MS)
    output_path = output_dir / capture.filename
    page.screenshot(path=str(output_path), full_page=True)
    return output_path


def run_capture() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright is not installed. Run:\n"
            "  pip install playwright\n"
            "  playwright install chromium",
            file=sys.stderr,
        )
        return 1

    base_url = resolve_base_url()
    site_url = resolve_site_url()
    output_dir = ensure_output_dir()

    try:
        username, password = read_credentials()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Base URL: {base_url}")
    print(f"Output:   {output_dir}")
    print(f"Viewport: {VIEWPORT_WIDTH}x{VIEWPORT_HEIGHT}")

    failures: list[str] = []
    successes: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": VIEWPORT_WIDTH, "height": VIEWPORT_HEIGHT},
        )
        page = context.new_page()
        try:
            authenticate(page, site_url, username, password)
            print("Authenticated successfully.")
        except Exception as exc:
            browser.close()
            print(f"ERROR: Login failed: {exc}", file=sys.stderr)
            return 1

        for capture in PAGE_CAPTURES:
            target_url = build_page_url(base_url, capture.path)
            print(f"Capturing {capture.label} -> {capture.filename}")
            print(f"  URL: {target_url}")
            try:
                output_path = capture_page(page, capture, base_url, output_dir)
                successes.append(str(output_path))
                print(f"  OK: {output_path}")
            except Exception as exc:
                failures.append(f"{capture.label} ({target_url}): {exc}")
                print(f"  FAILED: {exc}", file=sys.stderr)

        browser.close()

    print()
    print(f"Completed: {len(successes)} succeeded, {len(failures)} failed.")
    if failures:
        print("Failures:", file=sys.stderr)
        for item in failures:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("All Career Evidence screenshots captured.")
    return 0


def main() -> None:
    raise SystemExit(run_capture())


if __name__ == "__main__":
    main()
