from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.messages import constants
from django.contrib.messages.storage.base import Message
from django.template.loader import render_to_string
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.applications.choices import ApplicationStatus, FollowUpStatus
from apps.applications.models import JobApplication
from apps.daily_log.models import DailyLog
from apps.interviews.models import InterviewPrep
from apps.weekly_review.models import WeeklyReview

from .services import (
    TodayActionItem,
    build_dashboard_summary,
    build_evidence_readiness_summary,
    build_pipeline_health_matrix,
    build_recent_activity_timeline,
    build_today_action_panel,
    build_today_signals,
    build_week_pulse,
    get_current_week_range,
    should_prompt_weekly_review,
)

# Wednesday - not week-ending (Sunday), so empty-state tests stay CI-stable.
STABLE_NON_WEEK_END = date(2026, 5, 20)


class DashboardServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Test Company",
            "job_title": "Data Analyst",
            "job_url": "https://example.com/job",
            "required_skills": "SQL, Python",
            "job_description": "Analyse operational data and report findings.",
            "date_applied": timezone.localdate() - timedelta(days=7),
            "cv_version": "Data_CV_v1",
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_current_week_range_returns_start_before_end(self):
        week_start, week_end = get_current_week_range()
        self.assertLessEqual(week_start, week_end)

    def test_dashboard_summary_without_data_returns_zero_values(self):
        summary = build_dashboard_summary(self.user)
        self.assertEqual(summary.total_applications, 0)
        self.assertEqual(summary.response_rate, 0.0)

    def test_today_action_panel_identifies_rule_based_actions(self):
        today = timezone.localdate()
        overdue = self._create_application(
            company_name="Overdue Co",
            follow_up_date=today - timedelta(days=2),
            follow_up_status=FollowUpStatus.DUE,
        )
        self._create_application(
            company_name="Today Co",
            follow_up_date=today,
            follow_up_status=FollowUpStatus.NOT_SET,
        )
        self._create_application(
            company_name="Missing Data Co",
            cv_version="",
            job_url="",
            required_skills="",
            job_description="",
        )
        interview_application = self._create_application(
            company_name="Interview Co",
            status=ApplicationStatus.INTERVIEW,
        )
        InterviewPrep.objects.create(
            user=self.user,
            application=interview_application,
            interview_date=today + timedelta(days=2),
        )

        actions = build_today_action_panel(self.user, limit=8)
        titles = [action.title for action in actions]
        priority_rank = {"High": 0, "Medium": 1, "Low": 2}

        self.assertTrue(all(isinstance(action, TodayActionItem) for action in actions))
        self.assertIn("Overdue follow-up: Overdue Co", titles)
        self.assertIn("Follow up today: Today Co", titles)
        self.assertIn("Prepare for interview: Interview Co", titles)
        self.assertIn("Add CV version: Missing Data Co", titles)
        self.assertIn("Add job evidence: Missing Data Co", titles)
        self.assertIn("Add job URL: Missing Data Co", titles)
        self.assertIn("Add today's daily log", titles)
        self.assertIn(overdue.get_absolute_url(), [action.related_url for action in actions])
        self.assertEqual(
            [priority_rank[action.priority] for action in actions],
            sorted(priority_rank[action.priority] for action in actions),
        )

    def test_today_action_panel_respects_limit_after_priority_sorting(self):
        today = timezone.localdate()
        DailyLog.objects.create(user=self.user, log_date=today)
        self._create_application(company_name="Low Priority Co", job_url="")
        self._create_application(
            company_name="High Priority Co",
            follow_up_date=today - timedelta(days=1),
            follow_up_status=FollowUpStatus.DUE,
        )

        actions = build_today_action_panel(self.user, limit=1)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].priority, "High")
        self.assertEqual(actions[0].title, "Overdue follow-up: High Priority Co")

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_today_action_panel_returns_empty_when_nothing_needs_attention(
        self, _mock_localdate
    ):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)

        actions = build_today_action_panel(self.user)

        self.assertEqual(actions, [])


class DashboardViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Dashboard Co",
            "job_title": "Data Analyst",
            "job_url": "https://example.com/dashboard-job",
            "required_skills": "SQL, Python",
            "job_description": "Build dashboards and explain trends.",
            "date_applied": timezone.localdate() - timedelta(days=7),
            "cv_version": "Data_CV_v1",
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_loads_for_logged_in_user(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("today_action_panel", response.context)
        self.assertContains(response, "Today Signals")

    def test_dashboard_displays_today_action_panel_item(self):
        today = timezone.localdate()
        DailyLog.objects.create(user=self.user, log_date=today)
        application = self._create_application(
            company_name="Action Co",
            follow_up_date=today - timedelta(days=1),
            follow_up_status=FollowUpStatus.DUE,
        )

        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Overdue follow-up: Action Co")
        self.assertContains(response, "Send a short follow-up and update the follow-up status.")
        self.assertContains(response, application.get_absolute_url())

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_dashboard_displays_today_action_panel_empty_state(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)

        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["today_action_panel"], [])
        self.assertContains(response, "Command centre clear")


class DashboardMobileNavigationRegressionTests(TestCase):
    PROJECT_ROOT = Path(__file__).resolve().parents[2]

    def setUp(self):
        self.user = User.objects.create_user(
            username="mobile-nav-regression",
            password="StrongPass12345",
        )
        self.client.login(
            username="mobile-nav-regression",
            password="StrongPass12345",
        )

    def _read_css(self, relative_path: str) -> str:
        return (self.PROJECT_ROOT / relative_path).read_text(encoding="utf-8")

    def _read_sidebar_js(self) -> str:
        return (
            self.PROJECT_ROOT / "static/js/modules/sidebar.js"
        ).read_text(encoding="utf-8")

    def test_dashboard_renders_mobile_nav_toggle_markup(self):
        response = self.client.get(reverse("dashboard:overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="mobile-nav-toggle"')
        self.assertContains(response, "cf-mobile-nav-toggle")
        self.assertContains(response, 'aria-controls="app-sidebar"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, 'aria-label="Open navigation menu"')

    def test_components_css_preserves_base_display_none_contract(self):
        css = self._read_css("static/css/components.css")

        self.assertIn(
            ".cf-mobile-nav-toggle {\n"
            "    display: none;",
            css,
        )

    def test_components_css_contains_mobile_max_900_inline_flex_override(self):
        css = self._read_css("static/css/components.css")

        self.assertIn(
            "@media (max-width: 900px) {\n"
            "    .cf-mobile-nav-toggle {\n"
            "        display: inline-flex;\n"
            "    }\n"
            "}",
            css,
        )

    def test_components_css_mobile_override_follows_base_display_none(self):
        css = self._read_css("static/css/components.css")
        base_pos = css.index(".cf-mobile-nav-toggle {")
        display_none_pos = css.index("display: none;", base_pos)
        media_pos = css.index("@media (max-width: 900px)", display_none_pos)
        mobile_toggle_pos = css.index(".cf-mobile-nav-toggle", media_pos)
        inline_flex_pos = css.index("display: inline-flex;", mobile_toggle_pos)

        self.assertGreater(display_none_pos, base_pos)
        self.assertGreater(media_pos, display_none_pos)
        self.assertGreater(inline_flex_pos, media_pos)

    def test_layout_css_existing_mobile_rule_remains_present(self):
        css = self._read_css("static/css/layout.css")

        self.assertIn("@media (max-width: 900px)", css)
        self.assertIn(".cf-mobile-nav-toggle", css)
        self.assertIn("display: inline-flex", css)

    def test_sidebar_js_applies_inert_for_closed_mobile_drawer(self):
        js = self._read_sidebar_js()

        self.assertIn(
            'if (isMobile && !drawerIsOpen) {',
            js,
        )
        self.assertIn(
            'sidebar.setAttribute("inert", "");',
            js,
        )

    def test_sidebar_js_removes_inert_for_interactive_sidebar(self):
        js = self._read_sidebar_js()

        self.assertIn(
            'sidebar.removeAttribute("inert");',
            js,
        )

    def test_sidebar_js_preserves_closed_mobile_aria_hidden_contract(self):
        js = self._read_sidebar_js()

        self.assertIn(
            'sidebar.setAttribute("aria-hidden", "true");',
            js,
        )
        self.assertIn(
            'sidebar.removeAttribute("aria-hidden");',
            js,
        )

    def test_sidebar_js_preserves_mobile_toggle_expanded_contract(self):
        js = self._read_sidebar_js()

        self.assertIn(
            '"aria-expanded",',
            js,
        )
        self.assertIn(
            'drawerIsOpen ? "true" : "false"',
            js,
        )

    def test_sidebar_js_restores_focus_before_applying_closed_state(self):
        js = self._read_sidebar_js()

        close_start = js.index("function closeDrawer()")
        open_start = js.index("function openDrawer()", close_start)
        close_drawer = js[close_start:open_start]

        focus_pos = close_drawer.index("toggle.focus();")
        state_sync_pos = close_drawer.index("setDrawerOpen(")

        self.assertLess(focus_pos, state_sync_pos)
        self.assertIn(
            "sidebar.contains(document.activeElement)",
            close_drawer,
        )

    def test_sidebar_js_resynchronises_drawer_state_on_resize(self):
        js = self._read_sidebar_js()

        resize_start = js.index('window.addEventListener("resize"')
        resize_handler = js[resize_start:]

        self.assertIn("closeDrawer();", resize_handler)

    def test_sidebar_js_desktop_state_clears_stale_inert(self):
        js = self._read_sidebar_js()

        set_drawer_start = js.index("function setDrawerOpen(")
        update_button_start = js.index(
            "function updateReopenButton",
            set_drawer_start,
        )
        set_drawer_open = js[set_drawer_start:update_button_start]

        self.assertIn(
            "var isMobile = !isDesktopViewport();",
            set_drawer_open,
        )
        self.assertIn(
            "var drawerIsOpen = isMobile && isOpen;",
            set_drawer_open,
        )
        self.assertIn(
            'sidebar.removeAttribute("inert");',
            set_drawer_open,
        )
        self.assertIn(
            'sidebar.removeAttribute("aria-hidden");',
            set_drawer_open,
        )

class DashboardWeeklyOsPolishTests(TestCase):
    WEEK_END_SUNDAY = date(2026, 5, 10)

    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")

    def test_dashboard_contains_weekly_operating_rhythm_copy(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Weekly Operating Pipeline")
        self.assertContains(response, "Manual rhythm only")
        self.assertContains(response, "Capture")
        self.assertContains(response, reverse("daily_log:daily_log_list"))
        self.assertContains(response, reverse("weekly_review:weekly_review_list"))
        self.assertContains(response, reverse("ai_agents:weekly_coach"))

    @patch("apps.dashboard.services.timezone.localdate", return_value=WEEK_END_SUNDAY)
    def test_today_action_includes_weekly_review_prompt_on_week_end(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=self.WEEK_END_SUNDAY)
        actions = build_today_action_panel(self.user)
        titles = [action.title for action in actions]
        self.assertIn("Weekly review due", titles)

    @patch("apps.dashboard.services.timezone.localdate", return_value=WEEK_END_SUNDAY)
    def test_today_action_weekly_review_prompt_links_to_create(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=self.WEEK_END_SUNDAY)
        actions = build_today_action_panel(self.user)
        weekly_actions = [action for action in actions if action.title == "Weekly review due"]
        self.assertEqual(len(weekly_actions), 1)
        self.assertEqual(
            weekly_actions[0].related_url,
            reverse("weekly_review:weekly_review_create"),
        )
        self.assertIn("manual weekly review", weekly_actions[0].recommended_action)

    @patch("apps.dashboard.services.timezone.localdate", return_value=WEEK_END_SUNDAY)
    def test_today_action_weekly_review_prompt_not_shown_when_review_exists(
        self, _mock_localdate
    ):
        DailyLog.objects.create(user=self.user, log_date=self.WEEK_END_SUNDAY)
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 5, 4),
            week_ending=self.WEEK_END_SUNDAY,
        )
        self.assertFalse(should_prompt_weekly_review(self.user, self.WEEK_END_SUNDAY))
        actions = build_today_action_panel(self.user)
        titles = [action.title for action in actions]
        self.assertNotIn("Weekly review due", titles)

    def test_dashboard_get_does_not_mutate_applications_or_weekly_reviews(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Stable Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
        )
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 4, 27),
            week_ending=date(2026, 5, 3),
        )
        application_count_before = JobApplication.objects.filter(user=self.user).count()
        review_count_before = WeeklyReview.objects.filter(user=self.user).count()
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            JobApplication.objects.filter(user=self.user).count(),
            application_count_before,
        )
        self.assertEqual(
            WeeklyReview.objects.filter(user=self.user).count(),
            review_count_before,
        )

    def test_dashboard_copy_remains_manual_and_claim_safe(self):
        self.client.login(username="aminul", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "does not submit applications")
        self.assertContains(response, "send email")
        self.assertContains(response, "update statuses automatically")
        self.assertContains(response, "interview prep automatically")
        self.assertContains(response, "For week-level reflection")
        self.assertContains(response, "advisory risks")
        self.assertContains(response, "does not submit applications")


class DashboardCommandCentrePolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.client.login(username="aminul", password="StrongPass12345")

    def _sidebar_html(self, response):
        content = response.content.decode()
        marker_index = content.find('id="app-sidebar"')
        self.assertNotEqual(marker_index, -1)
        start = content.rfind("<aside", 0, marker_index)
        end = content.find("</aside>", marker_index)
        self.assertNotEqual(start, -1)
        self.assertNotEqual(end, -1)
        return content[start : end + len("</aside>")]

    def _topbar_html(self, response):
        content = response.content.decode()
        marker_index = content.find("cf-shell-topbar")
        self.assertNotEqual(marker_index, -1)
        start = content.rfind("<header", 0, marker_index)
        end = content.find("</header>", marker_index)
        self.assertNotEqual(start, -1)
        self.assertNotEqual(end, -1)
        return content[start : end + len("</header>")]

    def _create_application(self, **overrides):
        defaults = {
            "user": self.user,
            "company_name": "Command Co",
            "job_title": "Data Analyst",
            "job_url": "https://example.com/job",
            "required_skills": "SQL, Python",
            "job_description": "Analyze operational data.",
            "date_applied": timezone.localdate(),
            "cv_version": "Aminul_Islam_Data_Analyst_CV",
        }
        defaults.update(overrides)
        return JobApplication.objects.create(**defaults)

    def test_topbar_shell_renders_account_and_quick_add_controls(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        topbar = self._topbar_html(response)
        self.assertIn("cf-shell-topbar", topbar)
        self.assertIn('aria-label="Application header"', topbar)
        self.assertIn("cf-shell-topbar-actions", topbar)
        self.assertIn("cf-shell-topbar-menu", topbar)
        self.assertIn("cf-shell-user-menu", topbar)
        self.assertIn('data-topbar-menu', topbar)
        self.assertIn('data-topbar-menu-trigger', topbar)
        self.assertIn('aria-label="Open quick add menu"', topbar)
        self.assertIn('aria-label="Account menu for aminul"', topbar)
        self.assertIn(reverse("applications:application_create"), topbar)
        self.assertIn(reverse("daily_log:daily_log_create"), topbar)
        self.assertIn(reverse("weekly_review:weekly_review_create"), topbar)
        self.assertIn(reverse("notes:note_create"), topbar)
        self.assertIn(reverse("accounts:profile"), topbar)
        self.assertIn(reverse("accounts:settings"), topbar)

    def test_topbar_avoids_forbidden_claims_and_staff_links_for_standard_user(self):
        response = self.client.get(reverse("dashboard:overview"))
        topbar = self._topbar_html(response).lower()
        forbidden_claims = (
            "auto" + "-apply",
            "auto " + "apply",
            "automatic " + "submission",
            "send to " + "employer",
            "email " + "employer",
            "oa" + "uth",
            "gm" + "ail",
            "out" + "look",
            "background " + "task",
            "employer " + "verified",
            "external " + "verification",
            "hiring " + "prediction",
            "guaran" + "teed",
            "verified " + "mastery",
            "ai" + "-powered",
        )
        for phrase in forbidden_claims:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, topbar)
        self.assertNotIn("/admin/", topbar)
        self.assertNotIn(">admin<", topbar)
        self.assertNotIn(">staff<", topbar)

    def test_messages_partial_preserves_tags_and_semantics(self):
        html = render_to_string(
            "partials/messages.html",
            {
                "messages": [
                    Message(constants.SUCCESS, "Application saved.", ""),
                    Message(constants.WARNING, "Review the evidence first.", ""),
                    Message(constants.ERROR, "Action could not be completed.", ""),
                    Message(constants.INFO, "Manual review reminder.", ""),
                ]
            },
        )
        self.assertIn("cf-shell-messages", html)
        self.assertIn("message message-success", html)
        self.assertIn("message message-warning", html)
        self.assertIn("message message-error", html)
        self.assertIn("message message-info", html)
        self.assertIn("cf-shell-message-success", html)
        self.assertIn("cf-shell-message-warning", html)
        self.assertIn("cf-shell-message-error", html)
        self.assertIn("cf-shell-message-info", html)
        self.assertEqual(html.count('role="alert"'), 2)
        self.assertEqual(html.count('role="status"'), 2)
        self.assertIn("Application saved.", html)
        self.assertIn("Review the evidence first.", html)

    def test_sidebar_shell_renders_with_grouped_navigation(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        sidebar = self._sidebar_html(response)
        self.assertIn("cf-shell-sidebar", sidebar)
        self.assertIn('aria-label="Primary product navigation"', sidebar)
        self.assertIn('aria-label="Product workflow navigation"', sidebar)
        for section in (
            "Command",
            "Pipeline",
            "Review",
            "Intelligence",
            "Career Intelligence",
            "Reporting Suite",
            "Evidence",
        ):
            with self.subTest(section=section):
                self.assertIn(section, sidebar)

    def test_sidebar_contains_expected_primary_navigation_links(self):
        response = self.client.get(reverse("dashboard:overview"))
        sidebar = self._sidebar_html(response)
        for url_name in (
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
        ):
            with self.subTest(url_name=url_name):
                self.assertIn(reverse(url_name), sidebar)

    def test_sidebar_marks_current_dashboard_route_as_active(self):
        response = self.client.get(reverse("dashboard:overview"))
        sidebar = self._sidebar_html(response)
        self.assertEqual(sidebar.count('aria-current="page"'), 1)
        self.assertIn("cf-shell-nav-link-active", sidebar)
        self.assertIn(
            'href="{}" class="sidebar-link cf-nav-link cf-shell-nav-link active '
            'cf-shell-nav-link-active" aria-current="page"'.format(
                reverse("dashboard:overview")
            ),
            sidebar,
        )

    def test_sidebar_avoids_forbidden_claims_and_staff_links_for_standard_user(self):
        response = self.client.get(reverse("dashboard:overview"))
        sidebar = self._sidebar_html(response)
        sidebar_lower = sidebar.lower()
        forbidden_claims = (
            "auto" + "-apply",
            "auto " + "apply",
            "automatic " + "submission",
            "send to " + "employer",
            "email " + "employer",
            "oa" + "uth",
            "gm" + "ail",
            "out" + "look",
            "background " + "task",
            "employer " + "verified",
            "external " + "verification",
            "hiring " + "prediction",
            "guaran" + "teed",
            "verified " + "mastery",
            "ai" + "-powered",
        )
        for phrase in forbidden_claims:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, sidebar_lower)
        self.assertNotIn("/admin/", sidebar_lower)
        self.assertNotIn(">admin<", sidebar_lower)
        self.assertNotIn(">staff<", sidebar_lower)

    def test_dashboard_renders_career_command_centre_copy(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Analytics Command Centre")
        self.assertContains(response, "Calm authority for the manual job-search pipeline")
        self.assertContains(response, "Signature Career Insight")

    def test_dashboard_shows_week_pulse(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("week_pulse", response.context)
        self.assertContains(response, "Week Pulse")
        self.assertContains(response, response.context["week_pulse"].week_range_label)

    def test_dashboard_shows_pipeline_health_matrix(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("pipeline_health", response.context)
        self.assertContains(response, "Pipeline Health Matrix")
        self.assertEqual(len(response.context["pipeline_health"].metrics), 6)

    def test_dashboard_shows_evidence_readiness_summary(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("evidence_readiness", response.context)
        self.assertContains(response, "Evidence Readiness")
        self.assertContains(response, "Missing CV versions")

    def test_dashboard_today_signals_remain_manual_and_claim_safe(self):
        today = timezone.localdate()
        DailyLog.objects.create(user=self.user, log_date=today)
        self._create_application(
            company_name="Signal Co",
            follow_up_date=today - timedelta(days=1),
            follow_up_status=FollowUpStatus.DUE,
        )
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("today_signals", response.context)
        self.assertContains(response, "Today Signals")
        self.assertContains(response, "Send a short follow-up and update the follow-up status.")
        self.assertContains(response, "Open")

    def test_dashboard_get_does_not_mutate_records(self):
        JobApplication.objects.create(
            user=self.user,
            company_name="Stable Co",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 1),
        )
        WeeklyReview.objects.create(
            user=self.user,
            week_starting=date(2026, 4, 27),
            week_ending=date(2026, 5, 3),
        )
        application_count_before = JobApplication.objects.filter(user=self.user).count()
        review_count_before = WeeklyReview.objects.filter(user=self.user).count()
        log_count_before = DailyLog.objects.filter(user=self.user).count()
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            JobApplication.objects.filter(user=self.user).count(),
            application_count_before,
        )
        self.assertEqual(
            WeeklyReview.objects.filter(user=self.user).count(),
            review_count_before,
        )
        self.assertEqual(DailyLog.objects.filter(user=self.user).count(), log_count_before)

    def test_dashboard_links_to_manual_workflow_pages(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        for url_name in (
            "applications:application_create",
            "daily_log:daily_log_create",
            "weekly_review:weekly_review_create",
            "metrics:funnel_metrics",
            "followups:followup_list",
            "interviews:interview_list",
        ):
            with self.subTest(url_name=url_name):
                self.assertContains(response, reverse(url_name))

    def test_dashboard_phase_69a_loads_without_error_for_authenticated_user(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_phase_69a_preserves_reviewer_walkthrough_wording(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Reviewer walkthrough")
        self.assertContains(response, "How to assess this portfolio project")
        self.assertContains(response, "manual, advisory, deterministic job-search analytics app")
        self.assertContains(response, "Deliberately not implemented")

    def test_dashboard_phase_69a_preserves_manual_advisory_wording(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Manual workflow only")
        self.assertContains(response, "Advisory guidance")
        self.assertContains(response, "Open manual workflow")
        self.assertContains(response, "Manual rhythm only")

    def test_dashboard_phase_69a_preserves_deterministic_rule_based_wording(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Deterministic records")
        self.assertContains(response, "rule-based from saved applications")
        self.assertContains(response, "Calculated from authenticated tracker records")

    def test_dashboard_phase_69a_kpi_values_render_from_context(self):
        self._create_application(status=ApplicationStatus.ACKNOWLEDGED)
        response = self.client.get(reverse("dashboard:overview"))
        summary = response.context["summary"]
        self.assertContains(response, "Total Applications")
        self.assertContains(response, f">{summary.total_applications}<")
        self.assertContains(response, f">{summary.applications_this_week}<")
        self.assertContains(response, f">{summary.response_rate}%<")
        self.assertContains(response, f">{summary.interview_rate}%<")

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_dashboard_phase_69a_today_signals_or_safe_empty_state_renders(
        self, _mock_localdate
    ):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "Today Signals")
        content = response.content.decode()
        self.assertTrue(
            "Command centre clear" in content
            or "Nothing urgent needs attention right now." in content
        )

    def test_dashboard_phase_69a_funnel_snapshot_values_render(self):
        self._create_application(status=ApplicationStatus.INTERVIEW)
        response = self.client.get(reverse("dashboard:overview"))
        snapshot = response.context["funnel_snapshot"]
        self.assertContains(response, "Funnel Snapshot")
        self.assertContains(response, f">{snapshot.applications}<")
        self.assertContains(response, f">{snapshot.responses}<")
        self.assertContains(response, f">{snapshot.interviews}<")
        self.assertContains(response, f">{snapshot.offers}<")

    def test_dashboard_phase_69a_week_pulse_values_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        week_pulse = response.context["week_pulse"]
        self.assertContains(response, "Week Pulse")
        self.assertContains(response, week_pulse.week_range_label)
        self.assertContains(response, f">{week_pulse.target_applications}<")
        self.assertContains(response, f">{week_pulse.actual_applications}<")
        self.assertContains(response, f">{week_pulse.variance}<")

    def test_dashboard_phase_69a_evidence_readiness_values_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        readiness = response.context["evidence_readiness"]
        self.assertContains(response, "Evidence Readiness")
        self.assertContains(response, f">{readiness.missing_cv_versions}<")
        self.assertContains(response, f">{readiness.missing_job_descriptions}<")
        self.assertContains(response, "Data Quality Report")

    def test_dashboard_phase_69a_signature_insight_renders_when_present(self):
        response = self.client.get(reverse("dashboard:overview"))
        insight = response.context["signature_insight"]
        self.assertContains(response, "Signature Career Insight")
        content = response.content.decode()
        self.assertIn(insight.diagnosis.replace("'", "&#x27;"), content)
        self.assertIn(insight.best_manual_action.replace("'", "&#x27;"), content)

    def test_dashboard_phase_69a_does_not_render_invented_trend_indicators(self):
        response = self.client.get(reverse("dashboard:overview"))
        content = response.content.decode().lower()
        forbidden_trends = (
            "% increase",
            "% decrease",
            "trending up",
            "trending down",
            "upward trend",
            "downward trend",
        )
        for phrase in forbidden_trends:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_dashboard_phase_69a_unsafe_positive_action_labels_are_absent(self):
        response = self.client.get(reverse("dashboard:overview"))
        content = response.content.decode()
        unsafe_labels = (
            "Apply Now",
            "Submit Application",
            "Auto " + "Apply",
            "Send Application",
        )
        for label in unsafe_labels:
            with self.subTest(label=label):
                self.assertNotIn(f">{label}<", content)

    def test_dashboard_phase_69a_safe_manual_action_labels_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        for label in (
            "Log Application",
            "Weekly Review",
            "Follow-up Tracker",
            "Interview Prep",
            "Funnel Metrics",
            "Data Quality Report",
        ):
            with self.subTest(label=label):
                self.assertContains(response, label)

    def test_dashboard_phase_69a_scoped_zone_and_advisory_classes_render(self):
        response = self.client.get(reverse("dashboard:overview"))
        for class_name in (
            "cf69-zone-command",
            "cf69-zone-today",
            "cf69-zone-intelligence",
            "cf69-zone-actions",
            "cf69-advisory-info",
            "cf69-advisory-manual",
            "cf69-advisory-warning",
        ):
            with self.subTest(class_name=class_name):
                self.assertContains(response, class_name)

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_dashboard_empty_state_for_new_user(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Command centre clear")
        self.assertContains(response, "Recent Activity Timeline")
        self.assertContains(response, "Daily Log")
        self.assertEqual(build_week_pulse(self.user).target_applications, 0)
        self.assertEqual(build_evidence_readiness_summary(self.user).missing_cv_versions, 0)

    def test_dashboard_shows_recent_activity_timeline(self):
        application = self._create_application(company_name="Timeline Co")
        DailyLog.objects.create(
            user=self.user,
            log_date=timezone.localdate(),
            target_applications=2,
            actual_applications=1,
        )
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("recent_activity_timeline", response.context)
        self.assertContains(response, "Recent Activity Timeline")
        self.assertContains(response, "Timeline Co")
        timeline = build_recent_activity_timeline(self.user)
        self.assertTrue(any(item.title == application.company_name for item in timeline))

    def test_dashboard_shows_funnel_snapshot(self):
        self._create_application(status=ApplicationStatus.ACKNOWLEDGED)
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("funnel_snapshot", response.context)
        self.assertContains(response, "Funnel Snapshot")
        self.assertContains(response, "Applications")
        self.assertContains(response, "Responses")
        self.assertContains(response, "Interviews")
        self.assertContains(response, "Offers")

    def test_dashboard_does_not_claim_automation_or_live_saas(self):
        response = self.client.get(reverse("dashboard:overview"))
        self.assertContains(response, "does not submit applications")
        self.assertContains(response, "send email")
        self.assertContains(response, "update statuses automatically")
        self.assertContains(response, "create interview prep automatically")
        self.assertContains(response, "auto" + "-apply")
        self.assertContains(response, "background polling")
        self.assertContains(response, "live SaaS deployment")

    def test_build_pipeline_health_matrix_returns_six_metrics(self):
        matrix = build_pipeline_health_matrix(self.user)
        labels = [metric.label for metric in matrix.metrics]
        self.assertEqual(
            labels,
            [
                "Activity volume",
                "Evidence quality",
                "Follow-up discipline",
                "Interview readiness",
                "Weekly review discipline",
                "Response conversion",
            ],
        )

    @patch(
        "apps.dashboard.services.timezone.localdate",
        return_value=STABLE_NON_WEEK_END,
    )
    def test_build_today_signals_adds_info_when_no_urgent_actions(self, _mock_localdate):
        DailyLog.objects.create(user=self.user, log_date=STABLE_NON_WEEK_END)
        signals = build_today_signals(self.user)
        self.assertEqual(signals[0].priority, "Info")
        self.assertIn("Command centre clear", signals[0].title)


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class Sprint51ReviewerWalkthroughPolishTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="revdash", password="StrongPass12345")

    def test_dashboard_renders_reviewer_walkthrough_copy(self):
        self.client.login(username="revdash", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Reviewer walkthrough")
        self.assertContains(response, "How to assess this portfolio project")
        self.assertContains(response, "Skill Intelligence Dashboard")
        self.assertContains(response, "Deliberately not implemented")

    def test_sprint_51_reviewer_copy_remains_claim_safe(self):
        self.client.login(username="revdash", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        content = response.content.decode().lower()
        self.assertIn("manual workflow only", content)
        self.assertIn("deliberately not implemented", content)
        self.assertIn("automatic application submission", content)
        self.assertIn("automatic cv rewriting", content)
        self.assertNotIn("sprint 52", content)

    def test_no_sprint_52_text_on_dashboard_home(self):
        self.client.login(username="revdash", password="StrongPass12345")
        response = self.client.get(reverse("dashboard:overview"))
        self.assertNotContains(response, "Sprint 52")

    def test_sprint_51_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "templates" / "dashboard" / "overview.html",
            REPO_ROOT / "docs" / "evidence" / "sprint_51_final_reviewer_walkthrough_polish.md",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )


class Sprint124Phase2AIEngineeringEvidenceContractTests(TestCase):
    """Sprint 124 Phase 2: read-only AI engineering evidence contract."""

    def test_evidence_contract_builds_with_expected_capability_count(self):
        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_evidence,
            build_ai_engineering_summary,
        )

        evidence = build_ai_engineering_evidence()
        summary = build_ai_engineering_summary()

        self.assertEqual(len(evidence), 8)
        self.assertEqual(summary.capability_count, 8)

    def test_required_capabilities_are_present(self):
        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_evidence,
        )

        capabilities = {
            item.capability for item in build_ai_engineering_evidence()
        }

        self.assertEqual(
            capabilities,
            {
                "Evidence-grounded AI application workflow",
                "Controlled LLM provider boundary",
                "RAG and retrieval evaluation",
                "Bounded read-only tool-calling",
                "Claim-safety controls",
                "Human-in-the-loop review",
                "AI quality lifecycle",
                "Controlled live-provider canary",
            },
        )

    def test_execution_types_are_explicit_and_distinct(self):
        from apps.dashboard.ai_engineering_evidence import (
            EXECUTION_CONTROLLED_LIVE,
            EXECUTION_DETERMINISTIC,
            EXECUTION_HUMAN_REVIEW,
            EXECUTION_LLM_ASSISTED,
            EXECUTION_RAG,
            EXECUTION_RULE_BASED,
            EXECUTION_TOOL_CALLING,
            build_ai_engineering_evidence,
        )

        execution_types = {
            item.execution_type for item in build_ai_engineering_evidence()
        }

        self.assertTrue(
            {
                EXECUTION_DETERMINISTIC,
                EXECUTION_RULE_BASED,
                EXECUTION_HUMAN_REVIEW,
                EXECUTION_LLM_ASSISTED,
                EXECUTION_RAG,
                EXECUTION_TOOL_CALLING,
                EXECUTION_CONTROLLED_LIVE,
            }.issubset(execution_types)
        )

    def test_historical_evaluation_evidence_is_qualified(self):
        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_evidence,
        )

        by_capability = {
            item.capability: item
            for item in build_ai_engineering_evidence()
        }

        rag = by_capability["RAG and retrieval evaluation"]
        tools = by_capability["Bounded read-only tool-calling"]
        quality = by_capability["AI quality lifecycle"]

        self.assertIn("31 offline RAG evaluation cases passed", rag.historical_validation)
        self.assertIn("Sprint 122", rag.historical_validation)

        self.assertIn(
            "81 offline tool-assistant evaluation cases passed",
            tools.historical_validation,
        )
        self.assertIn("Sprint 122", tools.historical_validation)

        self.assertIn(
            "54 offline AI quality evaluation cases passed",
            quality.historical_validation,
        )
        self.assertIn("Sprint 122", quality.historical_validation)

    def test_evidence_contract_preserves_claim_boundaries(self):
        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_evidence,
        )

        evidence = build_ai_engineering_evidence()

        combined = " ".join(
            " ".join(
                (
                    item.capability,
                    item.execution_type,
                    item.evidence_source,
                    item.evaluation_mode,
                    item.historical_validation,
                    item.claim_boundary,
                    item.provenance,
                )
            )
            for item in evidence
        ).lower()

        forbidden_claims = (
            "production-grade autonomous ai agents",
            "100% accurate",
            "guaranteed accuracy",
            "guaranteed reliable",
            "autonomous job-application automation",
        )

        for phrase in forbidden_claims:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, combined)

    def test_unsupported_claim_flags_remain_false(self):
        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_summary,
        )

        summary = build_ai_engineering_summary()

        self.assertTrue(summary.human_review_required)
        self.assertFalse(summary.autonomous_agent_claim)
        self.assertFalse(summary.production_vector_database_claim)
        self.assertFalse(summary.enterprise_rag_claim)
        self.assertFalse(summary.autonomous_job_application_claim)
        self.assertFalse(summary.production_reliability_claim)

    def test_evidence_contract_is_deterministic(self):
        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_evidence,
            build_ai_engineering_summary,
        )

        self.assertEqual(
            build_ai_engineering_evidence(),
            build_ai_engineering_evidence(),
        )
        self.assertEqual(
            build_ai_engineering_summary(),
            build_ai_engineering_summary(),
        )

    def test_evidence_items_are_immutable(self):
        from dataclasses import FrozenInstanceError

        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_evidence,
        )

        item = build_ai_engineering_evidence()[0]

        with self.assertRaises(FrozenInstanceError):
            item.capability = "Changed"

    def test_evidence_module_has_no_provider_network_or_orm_dependency(self):
        import inspect

        import apps.dashboard.ai_engineering_evidence as evidence_module

        source = inspect.getsource(evidence_module).lower()

        forbidden_tokens = (
            "provider_factory",
            "claude_provider",
            "requests",
            "httpx",
            "socket",
            "urllib",
            "django.db",
            "subprocess",
            "os.environ",
            "getenv(",
        )

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)

class Sprint124Phase3AIEngineeringEvidencePageTests(TestCase):
    """Sprint 124 Phase 3: authenticated read-only AI evidence page."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint124-ai-evidence",
            password="StrongPass12345",
        )
        self.url = reverse("dashboard:career_evidence_ai_engineering")

    def test_ai_engineering_evidence_requires_login(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

    def test_ai_engineering_evidence_renders_for_authenticated_user(self):
        self.client.login(
            username="sprint124-ai-evidence",
            password="StrongPass12345",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Engineering Evidence")
        self.assertContains(response, "Evidence-grounded AI application workflow")
        self.assertContains(response, "Controlled LLM provider boundary")
        self.assertContains(response, "RAG and retrieval evaluation")
        self.assertContains(response, "Bounded read-only tool-calling")
        self.assertContains(response, "Claim-safety controls")
        self.assertContains(response, "Human-in-the-loop review")
        self.assertContains(response, "AI quality lifecycle")
        self.assertContains(response, "Controlled live-provider canary")

    def test_ai_engineering_evidence_preserves_qualified_historical_results(self):
        self.client.login(
            username="sprint124-ai-evidence",
            password="StrongPass12345",
        )

        response = self.client.get(self.url)

        self.assertContains(response, "31 offline RAG evaluation cases passed")
        self.assertContains(response, "81 offline tool-assistant evaluation cases passed")
        self.assertContains(response, "54 offline AI quality evaluation cases passed")
        self.assertContains(response, "validated Sprint 122 repository state")

    def test_ai_engineering_evidence_preserves_claim_boundaries(self):
        self.client.login(
            username="sprint124-ai-evidence",
            password="StrongPass12345",
        )

        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertIn("bounded tool-calling", content)
        self.assertIn("human review", content)
        self.assertIn("not production", content)
        self.assertNotIn("production-grade autonomous ai agents", content)
        self.assertNotIn("100% accurate", content)
        self.assertNotIn("guaranteed accuracy", content)
        self.assertNotIn("autonomous job-application automation", content)

    def test_career_evidence_index_links_to_ai_engineering_evidence(self):
        self.client.login(
            username="sprint124-ai-evidence",
            password="StrongPass12345",
        )

        response = self.client.get(reverse("dashboard:career_evidence_index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI engineering implementation proof")
        self.assertContains(response, self.url)
        self.assertContains(response, "Open AI Engineering Evidence")

    @patch(
        "socket.create_connection",
        side_effect=AssertionError("Network access is forbidden during evidence render."),
    )
    @patch(
        "socket.socket.connect",
        side_effect=AssertionError("Socket connection is forbidden during evidence render."),
    )
    def test_ai_engineering_evidence_render_makes_no_network_calls(
        self,
        mock_socket_connect,
        mock_create_connection,
    ):
        self.client.login(
            username="sprint124-ai-evidence",
            password="StrongPass12345",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        mock_create_connection.assert_not_called()
        mock_socket_connect.assert_not_called()

    @patch(
        "apps.dashboard.views.career_evidence_views.build_ai_engineering_summary"
    )
    @patch(
        "apps.dashboard.views.career_evidence_views.build_ai_engineering_evidence"
    )
    def test_ai_engineering_evidence_render_uses_read_only_evidence_builders(
        self,
        mock_build_evidence,
        mock_build_summary,
    ):
        from apps.dashboard.ai_engineering_evidence import (
            build_ai_engineering_evidence,
            build_ai_engineering_summary,
        )

        mock_build_evidence.return_value = build_ai_engineering_evidence()
        mock_build_summary.return_value = build_ai_engineering_summary()

        self.client.login(
            username="sprint124-ai-evidence",
            password="StrongPass12345",
        )

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        mock_build_evidence.assert_called_once_with()
        mock_build_summary.assert_called_once_with()

    def test_ai_engineering_evidence_view_has_no_provider_dependency(self):
        import inspect

        from apps.dashboard.views import career_evidence_views

        source = inspect.getsource(
            career_evidence_views.ai_engineering_evidence_detail
        ).lower()

        forbidden_tokens = (
            "provider_factory",
            "claude_provider",
            "compose_",
            "api_key",
            "requests",
            "httpx",
            "socket",
        )

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, source)


class Sprint124Phase4EvaluationSafetyEvidenceTests(TestCase):
    """Sprint 124 Phase 4: evaluation and claim-safety presentation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint124-evaluation-evidence",
            password="StrongPass12345",
        )
        self.client.login(
            username="sprint124-evaluation-evidence",
            password="StrongPass12345",
        )
        self.url = reverse("dashboard:career_evidence_ai_engineering")

    def test_evaluation_and_safety_section_renders(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evaluation &amp; Safety Evidence")
        self.assertContains(response, "How the AI workflow was evaluated")
        self.assertContains(response, "Qualified evidence")

    def test_offline_evaluation_is_distinguished_from_live_canary(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Offline deterministic")
        self.assertContains(response, "RAG and retrieval evaluation")
        self.assertContains(response, "Bounded read-only tool-calling")
        self.assertContains(response, "AI quality lifecycle")
        self.assertContains(response, "Controlled live evidence")
        self.assertContains(response, "Controlled live-provider canary")

    def test_historical_evaluation_counts_are_rendered_from_evidence_contract(self):
        response = self.client.get(self.url)

        self.assertContains(response, "31 offline RAG evaluation cases passed")
        self.assertContains(response, "81 offline tool-assistant evaluation cases passed")
        self.assertContains(response, "54 offline AI quality evaluation cases passed")
        self.assertContains(response, "validated Sprint 122 repository state")

    def test_claim_safety_evidence_surfaces_safe_rejection_and_alignment(self):
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertIn("safe-rejection", content)
        self.assertIn("evidence-alignment", content)
        self.assertIn("prompt-injection", content)
        self.assertIn("safe rejection behaviour", content)
        self.assertIn("prohibited-claim", content)

    def test_live_canary_remains_explicitly_qualified(self):
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertIn("one-call, zero-retry", content)
        self.assertIn("controlled integration evidence only", content)
        self.assertIn("does not prove production reliability", content)
        self.assertNotIn("production reliability proven", content)
        self.assertNotIn("production-grade autonomous ai agents", content)

    def test_evaluation_section_does_not_introduce_unsupported_infrastructure_claims(self):
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertNotIn("production vector database implemented", content)
        self.assertNotIn("enterprise rag infrastructure implemented", content)
        self.assertNotIn("autonomous agent implemented", content)
        self.assertNotIn("guaranteed accuracy", content)


class Sprint124Phase5RecruiterPortfolioProofTests(TestCase):
    """Sprint 124 Phase 5: recruiter-facing AI engineering proof."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint124-recruiter-proof",
            password="StrongPass12345",
        )
        self.client.login(
            username="sprint124-recruiter-proof",
            password="StrongPass12345",
        )
        self.url = reverse("dashboard:career_evidence_ai_engineering")

    def test_recruiter_proof_section_renders(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recruiter / Portfolio Proof")
        self.assertContains(response, "AI engineering evidence at a glance")
        self.assertContains(response, "Evidence-backed")

    def test_recruiter_proof_surfaces_core_engineering_evidence(self):
        response = self.client.get(self.url)

        self.assertContains(response, "Evidence-grounded AI application workflow")
        self.assertContains(response, "Controlled LLM provider boundary")
        self.assertContains(response, "Human-in-the-loop review")
        self.assertContains(response, "AI quality lifecycle")
        self.assertContains(response, "Controlled live-provider canary")

    def test_recruiter_summary_uses_approved_claim_safe_wording(self):
        response = self.client.get(self.url)

        self.assertContains(
            response,
            "Built an evidence-grounded AI application workflow",
        )
        self.assertContains(response, "controlled provider boundaries")
        self.assertContains(response, "offline evaluation")
        self.assertContains(response, "claim-safety controls")
        self.assertContains(response, "human review")

    def test_recruiter_proof_preserves_production_boundaries(self):
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertIn("does not claim autonomous job application", content)
        self.assertIn("enterprise rag", content)
        self.assertIn("production vector-database infrastructure", content)
        self.assertIn("production reliability", content)

    def test_recruiter_proof_does_not_claim_unsupported_capabilities(self):
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertNotIn("production-grade autonomous ai agents", content)
        self.assertNotIn("autonomous ai engineer", content)
        self.assertNotIn("enterprise rag implemented", content)
        self.assertNotIn("production vector database implemented", content)
        self.assertNotIn("guaranteed model accuracy", content)
        self.assertNotIn("fully autonomous job application", content)


class Sprint124Phase6RegressionPrivacyResponsiveUATTests(TestCase):
    """Sprint 124 Phase 6: regression, privacy, and responsive UAT."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="sprint124-phase6-uat",
            password="StrongPass12345",
        )
        self.url = reverse("dashboard:career_evidence_ai_engineering")

    def test_ai_evidence_page_remains_authenticated_only(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)

        self.client.login(
            username="sprint124-phase6-uat",
            password="StrongPass12345",
        )
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "AI Engineering Evidence")
        self.assertContains(response, "Authenticated access")
        self.assertContains(response, "Read-only evidence")

    def test_ai_evidence_render_remains_network_isolated(self):
        from unittest.mock import patch

        self.client.login(
            username="sprint124-phase6-uat",
            password="StrongPass12345",
        )

        with (
            patch(
                "socket.create_connection",
                side_effect=AssertionError(
                    "Network access is forbidden during AI evidence render."
                ),
            ) as mock_create_connection,
            patch(
                "socket.socket.connect",
                side_effect=AssertionError(
                    "Socket access is forbidden during AI evidence render."
                ),
            ) as mock_socket_connect,
        ):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        mock_create_connection.assert_not_called()
        mock_socket_connect.assert_not_called()

    def test_ai_evidence_page_does_not_expose_private_provider_telemetry(self):
        self.client.login(
            username="sprint124-phase6-uat",
            password="StrongPass12345",
        )
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        forbidden_tokens = (
            "api_key",
            "api key:",
            "authorization:",
            "bearer ",
            "raw prompt",
            "raw response",
            "request payload sha",
            "request-payload sha",
            "response sha",
            "raw-response hash",
            "input tokens:",
            "output tokens:",
            "actual_spend",
            "cost_usd",
        )

        for token in forbidden_tokens:
            with self.subTest(token=token):
                self.assertNotIn(token, content)

    def test_permanent_safety_wording_remains_on_authoritative_surfaces(self):
        from pathlib import Path

        application_form = Path(
            "templates/applications/application_form.html"
        ).read_text(encoding="utf-8")
        application_detail = Path(
            "templates/applications/application_detail.html"
        ).read_text(encoding="utf-8")
        jd_gap = Path(
            "templates/applications/jd_gap_aggregation.html"
        ).read_text(encoding="utf-8")
        learning_recommendations = Path(
            "templates/skills/learning_recommendations_report.html"
        ).read_text(encoding="utf-8")
        analyzer = Path(
            "templates/ai_agents/job_posting_analyzer.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "Pre-filling this form does not save your application.",
            application_form,
        )
        self.assertIn(
            "Saving creates a tracking record only.",
            application_form,
        )
        self.assertIn(
            "Documents are not generated here.",
            application_form,
        )
        self.assertIn(
            "Draft - tracking record only",
            application_form,
        )
        self.assertIn(
            "Follow-up email drafts are for manual use only.",
            application_detail,
        )
        self.assertIn(
            "Skill gap signals are advisory only.",
            jd_gap,
        )
        self.assertIn(
            "Learning recommendations are planning aids.",
            learning_recommendations,
        )
        self.assertIn(
            "Pre-fill Add Application",
            analyzer,
        )

    def test_ai_evidence_css_preserves_responsive_layout_contracts(self):
        from pathlib import Path

        css = Path("static/css/career_evidence.css").read_text(
            encoding="utf-8"
        )

        required_tokens = (
            ".cf124-ai-evidence-grid",
            ".cf124-evaluation-evidence-grid",
            ".cf124-safety-evidence-grid",
            ".cf124-recruiter-proof-grid",
            "@media (max-width: 1100px)",
            "@media (max-width: 900px)",
            "grid-template-columns: 1fr;",
            "min-width: 0;",
            "max-width: 100%;",
            "overflow-wrap: anywhere;",
            "word-break: break-word;",
        )

        for token in required_tokens:
            with self.subTest(token=token):
                self.assertIn(token, css)

    def test_ai_evidence_page_preserves_claim_safe_boundaries(self):
        self.client.login(
            username="sprint124-phase6-uat",
            password="StrongPass12345",
        )
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        required_boundaries = (
            "does not claim autonomous job application",
            "not production",
            "human review",
            "advisory",
        )

        for phrase in required_boundaries:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, content)

        forbidden_claims = (
            "production-grade autonomous ai agents",
            "fully autonomous job application",
            "enterprise rag implemented",
            "production vector database implemented",
            "guaranteed model accuracy",
            "production reliability proven",
            "100% accurate",
        )

        for phrase in forbidden_claims:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)
