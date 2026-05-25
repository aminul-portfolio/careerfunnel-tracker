"""Sprint 42 - JavaScript Dynamic UX Foundation safety tests."""

from __future__ import annotations

import re
from pathlib import Path

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "static"
TEMPLATES_DIR = REPO_ROOT / "templates"

SPRINT_42_JS_MODULES = (
    "js/app.js",
    "js/modules/sidebar.js",
    "js/modules/table-controls.js",
    "js/modules/filters.js",
    "js/modules/forms.js",
    "js/modules/toasts.js",
    "js/modules/confirmations.js",
    "js/modules/copy-evidence.js",
    "js/modules/report-accordions.js",
)

FORBIDDEN_JS_PATTERNS = (
    re.compile(r"\bfetch\s*\(", re.IGNORECASE),
    re.compile(r"XMLHttpRequest", re.IGNORECASE),
    re.compile(r"\$\.ajax", re.IGNORECASE),
    re.compile(r"setInterval\s*\(", re.IGNORECASE),
    re.compile(r"auto-apply", re.IGNORECASE),  # forbidden safety pattern
    re.compile(r"auto-send", re.IGNORECASE),  # forbidden safety pattern
    re.compile(r"\bscraping\b", re.IGNORECASE),  # forbidden safety pattern
    re.compile(r"\bgmail\b", re.IGNORECASE),
    re.compile(r"\boauth\b", re.IGNORECASE),  # forbidden safety pattern
    re.compile(r"predictive\s+ai", re.IGNORECASE),
    re.compile(r"live\s+saas", re.IGNORECASE),
    re.compile(r"production\s+deployment", re.IGNORECASE),
)

CLAIM_SAFE_JS_MARKERS = (
    "localStorage",
    "cf-sidebar-collapsed",
)

APP_SCRIPT_CHAIN_MARKERS = (
    "js/modules/toasts.js",
    "js/app.js",
)


class Sprint42JavaScriptFoundationTests(TestCase):
    username = "jsuxuser"
    password = "StrongPass12345"

    def setUp(self):
        self.user = User.objects.create_user(
            username=self.username,
            password=self.password,
        )
        self.client.login(username=self.username, password=self.password)

    def test_sprint_42_static_javascript_modules_exist(self):
        for static_path in SPRINT_42_JS_MODULES:
            with self.subTest(static_path=static_path):
                self.assertTrue((STATIC_DIR / static_path).is_file())

    def test_base_template_references_approved_js_entry_chain(self):
        base_content = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
        for marker in APP_SCRIPT_CHAIN_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, base_content)
        self.assertIn('id="cf-toast-root"', base_content)

    def test_core_pages_render_primary_content_before_scripts(self):
        pages = (
            reverse("dashboard:overview"),
            reverse("applications:application_list"),
            reverse("metrics:funnel_metrics"),
            reverse("job_intelligence:skill_intelligence"),
        )
        for page_url in pages:
            with self.subTest(page_url=page_url):
                response = self.client.get(page_url)
                self.assertEqual(response.status_code, 200)
                content = response.content.decode()
                self.assertRegex(content, r"<h1\b")
                script_index = content.index('src="/static/js/app.js"')
                heading_index = content.index("<h1")
                self.assertLess(heading_index, script_index)

    def test_shell_mobile_and_collapse_hooks_exist(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('id="mobile-nav-toggle"', content)
        self.assertIn('id="sidebar-overlay"', content)
        self.assertIn('id="sidebar-collapse-toggle"', content)
        self.assertIn("data-cf-sidebar-collapse", content)

    def test_reporting_and_table_hooks_exist(self):
        metrics = self.client.get(reverse("metrics:funnel_metrics"))
        self.assertEqual(metrics.status_code, 200)
        self.assertContains(metrics, "data-cf-report-accordions")
        self.assertContains(metrics, "/static/js/modules/funnel-charts.js")
        self.assertNotContains(metrics, ("cd" + "n.") + "jsdelivr.net")

        applications = self.client.get(reverse("applications:application_list"))
        self.assertEqual(applications.status_code, 200)
        self.assertContains(applications, "data-cf-client-table-filter")
        self.assertContains(applications, "data-cf-table-filter-input")

    def test_career_evidence_copy_hook_exists(self):
        response = self.client.get(reverse("dashboard:career_evidence_index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "data-cf-copy=")
        self.assertContains(response, "Copy path")

    def test_js_modules_avoid_forbidden_automation_patterns(self):
        offenders: list[str] = []
        for static_path in SPRINT_42_JS_MODULES:
            content = (STATIC_DIR / static_path).read_text(encoding="utf-8")
            for pattern in FORBIDDEN_JS_PATTERNS:
                if pattern.search(content):
                    offenders.append(f"{static_path}: {pattern.pattern}")
        self.assertEqual(offenders, [])

    def test_js_modules_use_progressive_local_enhancements(self):
        sidebar = (STATIC_DIR / "js/modules/sidebar.js").read_text(encoding="utf-8")
        table_controls = (STATIC_DIR / "js/modules/table-controls.js").read_text(
            encoding="utf-8"
        )
        for marker in CLAIM_SAFE_JS_MARKERS:
            with self.subTest(marker=marker):
                self.assertIn(marker, sidebar)
        self.assertIn("visible row(s) on this page", table_controls)

    def test_app_js_does_not_inject_dom_content(self):
        app_js = (STATIC_DIR / "js/app.js").read_text(encoding="utf-8")
        self.assertNotIn("innerHTML", app_js)
        self.assertNotIn("document.write", app_js)

    def test_no_sprint_43_copy_in_templates_or_js(self):
        for path in sorted((STATIC_DIR / "js").rglob("*.js")):
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("Sprint 43", content, msg=str(path))
        base_content = (TEMPLATES_DIR / "base.html").read_text(encoding="utf-8")
        self.assertNotIn("Sprint 43", base_content)

    def test_no_job_intelligence_models_module(self):
        import importlib.util

        self.assertIsNone(importlib.util.find_spec("apps.job_intelligence.models"))
