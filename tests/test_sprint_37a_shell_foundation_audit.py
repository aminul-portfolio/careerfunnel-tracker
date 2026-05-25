"""Sprint 37A - shell, URL, static, and template safety audit tests."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import NoReverseMatch, reverse
from django.utils import timezone

from apps.applications.models import JobApplication
from apps.recruiter_emails.services import create_recruiter_email_from_form_data

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates"
STATIC_DIR = REPO_ROOT / "static"

SIDEBAR_URL_NAMES = (
    "dashboard:overview",
    "applications:application_list",
    "applications:evaluation_queue",
    "followups:followup_list",
    "interviews:interview_list",
    "daily_log:daily_log_list",
    "weekly_review:weekly_review_list",
    "notes:note_list",
    "job_intelligence:smart_review",
    "job_intelligence:skill_intelligence",
    "ai_agents:agent_dashboard",
    "metrics:funnel_metrics",
    "exports:export_center",
    "dashboard:career_evidence_index",
)

PRODUCT_NAV_GROUPS = (
    "Command",
    "Pipeline",
    "Review",
    "Intelligence",
    "Reporting Suite",
    "Evidence",
    "Account",
)

QUICK_ADD_URL_NAMES = (
    "applications:application_create",
    "daily_log:daily_log_create",
    "weekly_review:weekly_review_create",
    "notes:note_create",
)

QUICK_ADD_LABELS = (
    "Add Application",
    "Add Daily Log",
    "Add Weekly Review",
    "Add Note",
)

NAVBAR_URL_NAMES = (
    "accounts:logout",
    "accounts:login",
    "accounts:register",
)

REQUIRED_STATIC_FILES = (
    "css/tokens.css",
    "css/layout.css",
    "css/components.css",
    "css/career_evidence.css",
    "js/app.js",
)

REQUIRED_TOKEN_VARIABLES = (
    "--color-primary",
    "--color-muted",
    "--color-text",
    "--border-soft",
    "--shadow-soft",
    "--radius-md",
    "--radius-lg",
    "--font-main",
    "--focus-ring",
    "--sidebar-width",
)

CORE_STYLESHEETS = (
    "/static/css/tokens.css",
    "/static/css/layout.css",
    "/static/css/components.css",
)

APP_SCRIPT_MARKER = '<script src="/static/js/app.js"'

MAJOR_AUTHENTICATED_PAGES = (
    ("dashboard:overview", {}, "Premium manual job-search command centre"),
    ("applications:application_list", {}, "Track every application honestly"),
    ("applications:evaluation_queue", {}, "Evaluation Queue"),
    ("daily_log:daily_log_list", {}, "Track target vs actual every day"),
    ("weekly_review:weekly_review_list", {}, "Review the funnel every week"),
    ("interviews:interview_list", {}, "Turn interviews into structured evidence preparation"),
    ("notes:note_list", {}, "Store the decisions behind your job search"),
    ("followups:followup_list", {}, "Never lose an application after submission"),
    ("job_intelligence:smart_review", {}, "Score fit, readiness, CV choice, and project evidence"),
    ("job_intelligence:skill_intelligence", {}, "Manual, evidence-based skill review"),
    ("ai_agents:agent_dashboard", {}, "Turn tracker data into next actions"),
    ("metrics:funnel_metrics", {}, "Premium Reporting Foundation"),
    ("exports:export_center", {}, "Download reviewer-ready tracker evidence"),
)

STATIC_TAG_PATTERN = re.compile(r"\{%\s*static\s+['\"]([^'\"]+)['\"]")
INVALID_DASHBOARD_HOME_PATTERN = re.compile(r"dashboard:home")


class Sprint37AShellFoundationAuditMixin:
    username = "audituser"
    password = "StrongPass12345"

    def setUp(self):
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.client.login(username=self.username, password=self.password)


class SidebarAndNavbarUrlResolutionTests(TestCase):
    def test_sidebar_url_names_resolve(self):
        for url_name in SIDEBAR_URL_NAMES:
            with self.subTest(url_name=url_name):
                path = reverse(url_name)
                self.assertTrue(path.startswith("/"))

    def test_navbar_url_names_resolve(self):
        for url_name in NAVBAR_URL_NAMES:
            with self.subTest(url_name=url_name):
                reverse(url_name)

    def test_root_redirect_targets_dashboard_overview(self):
        response = self.client.get("/")
        self.assertRedirects(
            response,
            reverse("dashboard:overview"),
            fetch_redirect_response=False,
        )


class InvalidDashboardHomeReferenceTests(TestCase):
    def test_no_dashboard_home_url_name_in_templates(self):
        offenders: list[str] = []
        for template_path in sorted(TEMPLATES_DIR.rglob("*.html")):
            content = template_path.read_text(encoding="utf-8")
            if INVALID_DASHBOARD_HOME_PATTERN.search(content):
                offenders.append(template_path.relative_to(REPO_ROOT).as_posix())
        self.assertEqual(
            offenders,
            [],
            msg=f"Invalid dashboard:home references found in: {offenders}",
        )

    def test_dashboard_home_is_not_registered(self):
        with self.assertRaises(NoReverseMatch):
            reverse("dashboard:home")


class RequiredStaticReferenceTests(TestCase):
    def test_required_static_source_files_exist(self):
        for static_path in REQUIRED_STATIC_FILES:
            with self.subTest(static_path=static_path):
                full_path = STATIC_DIR / static_path
                self.assertTrue(
                    full_path.is_file(),
                    msg=f"Missing static source file: static/{static_path}",
                )

    def test_template_static_tags_reference_existing_source_files(self):
        missing: list[str] = []
        for template_path in sorted(TEMPLATES_DIR.rglob("*.html")):
            content = template_path.read_text(encoding="utf-8")
            for match in STATIC_TAG_PATTERN.findall(content):
                static_file = STATIC_DIR / match
                if not static_file.is_file():
                    rel_template = template_path.relative_to(REPO_ROOT).as_posix()
                    missing.append(f"{rel_template} -> static/{match}")
        self.assertEqual(missing, [], msg=f"Broken static references: {missing}")


class DesignSystemLockTests(TestCase):
    def test_tokens_css_defines_foundation_custom_properties(self):
        tokens_content = (STATIC_DIR / "css" / "tokens.css").read_text(encoding="utf-8")
        for variable_name in REQUIRED_TOKEN_VARIABLES:
            with self.subTest(variable_name=variable_name):
                self.assertIn(
                    variable_name,
                    tokens_content,
                    msg=f"Design token {variable_name} must remain defined in tokens.css",
                )

    def test_app_js_enhances_shell_without_dom_content_injection(self):
        app_js_content = (STATIC_DIR / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn(".sidebar-link", app_js_content)
        self.assertIn("classList.add(\"active\")", app_js_content)
        self.assertIn("aria-current", app_js_content)
        self.assertIn("mobile-nav-toggle", app_js_content)
        self.assertIn("Escape", app_js_content)
        self.assertNotIn("innerHTML", app_js_content)
        self.assertNotIn("document.write", app_js_content)


class BaseShellStylesheetTests(Sprint37AShellFoundationAuditMixin, TestCase):
    def test_authenticated_shell_includes_core_stylesheet_chain(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        for stylesheet_href in CORE_STYLESHEETS:
            with self.subTest(stylesheet_href=stylesheet_href):
                self.assertContains(response, stylesheet_href)


class ShellAccessibilityLandmarkTests(Sprint37AShellFoundationAuditMixin, TestCase):
    def test_authenticated_shell_includes_basic_landmarks(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('<html lang="en"', content)
        self.assertIn('<aside class="sidebar cf-sidebar"', content)
        self.assertIn('<nav class="sidebar-nav cf-sidebar-nav"', content)
        self.assertIn('<main class="main-content cf-main-content"', content)
        self.assertIn('<header class="topbar cf-topbar">', content)
        self.assertIn('<section class="page-content">', content)


class Sprint38PremiumShellTests(Sprint37AShellFoundationAuditMixin, TestCase):
    def test_dashboard_renders_premium_shell(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Job Search Operating System")
        self.assertContains(response, "Local Portfolio Demo")
        self.assertContains(response, "cf-trust-badge")
        self.assertContains(response, "cf-topbar")
        self.assertContains(response, "cf-sidebar")

    def test_sidebar_contains_product_navigation_groups(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        for group_label in PRODUCT_NAV_GROUPS:
            with self.subTest(group_label=group_label):
                self.assertContains(response, group_label)

    def test_sidebar_links_resolve_to_valid_urls(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        for url_name in SIDEBAR_URL_NAMES:
            with self.subTest(url_name=url_name):
                self.assertContains(response, reverse(url_name))

    def test_topbar_contains_quick_add_menu(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Quick Add")
        for label in QUICK_ADD_LABELS:
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_quick_add_links_are_manual_create_links_only(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        for url_name in QUICK_ADD_URL_NAMES:
            with self.subTest(url_name=url_name):
                self.assertContains(response, reverse(url_name))

    def test_mobile_drawer_controls_exist(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="mobile-nav-toggle"', content)
        self.assertIn('id="sidebar-overlay"', content)
        self.assertIn('aria-controls="app-sidebar"', content)

    def test_shell_supports_aria_current_on_active_navigation(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        app_js_content = (STATIC_DIR / "js" / "app.js").read_text(encoding="utf-8")
        self.assertIn('setAttribute("aria-current", "page")', app_js_content)

    def test_claim_safe_trust_badges_present(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Manual")
        self.assertContains(response, "Advisory")
        self.assertContains(response, "Evidence-based")

    def test_user_menu_contains_profile_settings_logout(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Profile")
        self.assertContains(response, "Settings")
        self.assertContains(response, "Logout")


class MajorAuthenticatedPageRenderTests(Sprint37AShellFoundationAuditMixin, TestCase):
    def test_major_authenticated_pages_render_successfully(self):
        for url_name, url_kwargs, expected_text in MAJOR_AUTHENTICATED_PAGES:
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name, kwargs=url_kwargs))
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)

    def test_recruiter_email_import_and_detail_pages_render(self):
        application = JobApplication.objects.create(
            user=self.user,
            company_name="Audit Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
        )
        recruiter_email = create_recruiter_email_from_form_data(
            application=application,
            cleaned_data={
                "subject": "Interview invitation",
                "sender_name": "Recruiter",
                "sender_email": "recruiter@example.com",
                "body": "We would like to invite you to interview.",
                "date_received": timezone.now(),
                "notes": "",
            },
        )

        import_response = self.client.get(
            reverse(
                "recruiter_emails:import",
                kwargs={"application_id": application.pk},
            )
        )
        self.assertEqual(import_response.status_code, 200)
        self.assertContains(import_response, "Import Recruiter Email")

        detail_response = self.client.get(
            reverse("recruiter_emails:detail", kwargs={"pk": recruiter_email.pk})
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Interview invitation")


class ServerSideShellRenderTests(Sprint37AShellFoundationAuditMixin, TestCase):
    def test_primary_page_content_renders_before_app_script(self):
        pages = (
            reverse("dashboard:overview"),
            reverse("applications:application_list"),
            reverse("metrics:funnel_metrics"),
            reverse("exports:export_center"),
        )
        for page_url in pages:
            with self.subTest(page_url=page_url):
                self._assert_primary_content_renders_before_app_script(page_url)

    def test_all_major_authenticated_pages_render_primary_content_before_app_script(self):
        for url_name, url_kwargs, _expected_text in MAJOR_AUTHENTICATED_PAGES:
            with self.subTest(url_name=url_name):
                page_url = reverse(url_name, kwargs=url_kwargs)
                self._assert_primary_content_renders_before_app_script(page_url)

    def _assert_primary_content_renders_before_app_script(self, page_url: str) -> None:
        response = self.client.get(page_url)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertRegex(content, r"<h1\b")
        self.assertIn(APP_SCRIPT_MARKER, content)
        heading_index = content.index("<h1")
        script_index = content.index(APP_SCRIPT_MARKER)
        self.assertLess(
            heading_index,
            script_index,
            msg="Primary heading must render before app.js for SSR safety",
        )

    def test_sidebar_navigation_links_are_present_in_server_html(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        for url_name in SIDEBAR_URL_NAMES:
            with self.subTest(url_name=url_name):
                self.assertContains(response, reverse(url_name))
