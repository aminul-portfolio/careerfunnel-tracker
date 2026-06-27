import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication
from apps.skill_ledger.models import SkillEntry

from .ai_career_coach import (
    EVIDENCE_PAYLOAD_KEYS,
    REQUIRED_PROMPT_SAFETY_RULES,
    build_controlled_prompt,
    build_evidence_payload,
    build_mocked_career_coach_response,
    expected_response_schema,
    validate_career_coach_response,
)
from .models import (
    ApplicationSkillGap,
    SkillGapIdentifiedBy,
    SkillGapLongTermGoal,
    SkillGapPriority,
    SkillGapStage,
    SkillTier,
)
from .services import (
    FAILURE_STATUSES,
    assign_priority,
    build_skill_gap_action_plan_context,
    build_skill_gap_cv_bullet_mapping_context,
    build_skill_gap_dashboard_context,
    build_skill_gap_evidence_readiness_context,
    build_skill_gap_interview_story_mapping_context,
    build_skill_gap_learning_plan_context,
    build_skill_gap_ledger_match_rows,
    build_skill_gap_portfolio_evidence_mapping_context,
    compute_priority_score,
    create_or_update_gap,
    get_action_plan_items,
    get_cv_bullet_mapping_items,
    get_evidence_readiness_items,
    get_global_failure_count,
    get_goal_weight,
    get_interview_story_mapping_items,
    get_learning_plan_items,
    get_portfolio_evidence_mapping_items,
    get_stage_weight,
    mark_gap_resolved,
    normalise_skill_match_key,
)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class ApplicationSkillGapModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="aminul", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
            required_skills="Python SQL",
        )

    def test_application_skill_gap_can_be_created(self):
        gap = ApplicationSkillGap.objects.create(
            application=self.application,
            stage=SkillGapStage.APPLICATION,
            skill_name="Python",
            current_tier=SkillTier.MISSING,
            priority=SkillGapPriority.MEDIUM,
            goal_weight=Decimal("1.00"),
            failure_count=1,
            stage_weight=Decimal("1.00"),
            priority_score=Decimal("1.00"),
            identified_by=SkillGapIdentifiedBy.MANUAL,
        )
        self.assertEqual(gap.skill_name, "Python")
        self.assertEqual(gap.application, self.application)

    def test_unique_constraint_prevents_duplicate_application_skill_stage(self):
        ApplicationSkillGap.objects.create(
            application=self.application,
            stage=SkillGapStage.APPLICATION,
            skill_name="SQL",
            current_tier=SkillTier.EMERGING,
            priority=SkillGapPriority.LOW,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=Decimal("0.00"),
            identified_by=SkillGapIdentifiedBy.MANUAL,
        )
        with self.assertRaises(IntegrityError):
            ApplicationSkillGap.objects.create(
                application=self.application,
                stage=SkillGapStage.APPLICATION,
                skill_name="SQL",
                current_tier=SkillTier.MISSING,
                priority=SkillGapPriority.HIGH,
                goal_weight=Decimal("1.00"),
                failure_count=2,
                stage_weight=Decimal("1.00"),
                priority_score=Decimal("2.00"),
                identified_by=SkillGapIdentifiedBy.RULE_BASED,
            )

    def test_model_meta_constraints_and_indexes_exist(self):
        meta = ApplicationSkillGap._meta
        constraint_names = {constraint.name for constraint in meta.constraints}
        index_names = {index.name for index in meta.indexes}
        self.assertIn("uniq_application_skill_gap_stage", constraint_names)
        self.assertEqual(
            index_names,
            {
                "skill_gap_application_idx",
                "skill_gap_stage_idx",
                "skill_gap_priority_idx",
                "skill_gap_skill_name_idx",
                "skill_gap_resolved_idx",
            },
        )


class SkillGapServiceScoringTests(TestCase):
    def test_compute_priority_score_is_deterministic(self):
        score_a = compute_priority_score(
            failure_count=2,
            stage_weight=Decimal("1.50"),
            goal_weight=Decimal("1.10"),
        )
        score_b = compute_priority_score(
            failure_count=2,
            stage_weight=Decimal("1.50"),
            goal_weight=Decimal("1.10"),
        )
        self.assertEqual(score_a, Decimal("3.30"))
        self.assertEqual(score_a, score_b)

    def test_assign_priority_returns_expected_bands(self):
        self.assertEqual(assign_priority(Decimal("10.00")), SkillGapPriority.CRITICAL)
        self.assertEqual(assign_priority(Decimal("6.00")), SkillGapPriority.HIGH)
        self.assertEqual(assign_priority(Decimal("3.00")), SkillGapPriority.MEDIUM)
        self.assertEqual(assign_priority(Decimal("1.00")), SkillGapPriority.LOW)

    def test_stage_and_goal_weights_work(self):
        self.assertEqual(get_stage_weight(SkillGapStage.TECHNICAL), Decimal("1.50"))
        self.assertEqual(
            get_goal_weight(SkillGapLongTermGoal.DATA_ENGINEER),
            Decimal("1.15"),
        )


class SkillGapLedgerMatchingServiceTests(TestCase):
    def _entry(self, skill_name, evidence_level):
        return SimpleNamespace(skill_name=skill_name, evidence_level=evidence_level)

    def _rows(self, gap_terms, skill_entries):
        return build_skill_gap_ledger_match_rows(gap_terms, skill_entries)

    def test_normalise_skill_match_key_handles_empty_string(self):
        self.assertEqual(normalise_skill_match_key(""), "")
        self.assertEqual(normalise_skill_match_key("   "), "")
        self.assertEqual(normalise_skill_match_key(None), "")

    def test_normalise_skill_match_key_applies_alias_map(self):
        self.assertEqual(normalise_skill_match_key("PowerBI"), "power bi")
        self.assertEqual(normalise_skill_match_key("power-bi"), "power bi")
        self.assertEqual(normalise_skill_match_key("SQL Server"), "sql")

    def test_normalise_skill_match_key_covers_all_aliases(self):
        expected_aliases = {
            "powerbi": "power bi",
            "power-bi": "power bi",
            "sql server": "sql",
            "stakeholders": "stakeholder",
            "ms fabric": "microsoft fabric",
            "dbt core": "dbt",
        }

        for alias, canonical in expected_aliases.items():
            with self.subTest(alias=alias):
                self.assertEqual(normalise_skill_match_key(alias), canonical)

    def test_build_skill_gap_ledger_match_rows_marks_verified_entry(self):
        rows = self._rows(
            [{"term": "Python", "frequency": 3}],
            [self._entry("Python", SkillEntry.EvidenceLevel.VERIFIED)],
        )

        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.VERIFIED)
        self.assertEqual(rows[0]["display_label"], SkillEntry.EvidenceLevel.VERIFIED)
        self.assertTrue(rows[0]["is_in_ledger"])

    def test_build_skill_gap_ledger_match_rows_marks_learning_target_entry(self):
        rows = self._rows(
            [{"term": "Snowflake", "frequency": 2}],
            [self._entry("Snowflake", SkillEntry.EvidenceLevel.LEARNING_TARGET)],
        )

        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.LEARNING_TARGET)
        self.assertEqual(rows[0]["display_label"], SkillEntry.EvidenceLevel.LEARNING_TARGET)
        self.assertTrue(rows[0]["is_in_ledger"])

    def test_build_skill_gap_ledger_match_rows_marks_studying_entry(self):
        rows = self._rows(
            [{"term": "Statistics", "frequency": 1}],
            [self._entry("Statistics", SkillEntry.EvidenceLevel.STUDYING)],
        )

        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.STUDYING)
        self.assertEqual(rows[0]["display_label"], SkillEntry.EvidenceLevel.STUDYING)
        self.assertTrue(rows[0]["is_in_ledger"])

    def test_build_skill_gap_ledger_match_rows_marks_no_evidence_entry(self):
        rows = self._rows(
            [{"term": "GraphQL", "frequency": 1}],
            [self._entry("GraphQL", SkillEntry.EvidenceLevel.NO_EVIDENCE)],
        )

        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.NO_EVIDENCE)
        self.assertEqual(rows[0]["display_label"], SkillEntry.EvidenceLevel.NO_EVIDENCE)
        self.assertTrue(rows[0]["is_in_ledger"])

    def test_build_skill_gap_ledger_match_rows_marks_not_in_ledger_when_no_match_exists(self):
        rows = self._rows(
            [{"term": "Airflow", "frequency": 2}],
            [self._entry("Python", SkillEntry.EvidenceLevel.VERIFIED)],
        )

        self.assertEqual(rows[0]["ledger_status"], "NOT_IN_LEDGER")
        self.assertEqual(rows[0]["display_label"], "Not in Skill Ledger")
        self.assertEqual(rows[0]["matched_skill_name"], "")
        self.assertFalse(rows[0]["is_in_ledger"])

    def test_build_skill_gap_ledger_match_rows_uses_normalised_exact_match(self):
        rows = self._rows(
            [{"term": "  POWER   BI  ", "frequency": 4}],
            [self._entry("power bi", SkillEntry.EvidenceLevel.VERIFIED)],
        )

        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.VERIFIED)
        self.assertEqual(rows[0]["matched_skill_name"], "power bi")

    def test_build_skill_gap_ledger_match_rows_uses_explicit_alias_mapping(self):
        rows = self._rows(
            [{"term": "sql server", "frequency": 5}],
            [self._entry("SQL", SkillEntry.EvidenceLevel.VERIFIED)],
        )

        self.assertEqual(rows[0]["term"], "sql server")
        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.VERIFIED)
        self.assertEqual(rows[0]["matched_skill_name"], "SQL")

    def test_build_skill_gap_ledger_match_rows_does_not_use_substring_false_positive(self):
        rows = self._rows(
            [{"term": "sql", "frequency": 5}],
            [self._entry("NoSQL", SkillEntry.EvidenceLevel.VERIFIED)],
        )

        self.assertEqual(rows[0]["ledger_status"], "NOT_IN_LEDGER")
        self.assertFalse(rows[0]["is_in_ledger"])

    def test_build_skill_gap_ledger_match_rows_returns_matched_skill_name(self):
        rows = self._rows(
            [{"term": "dbt core", "frequency": 2}],
            [self._entry("dbt", SkillEntry.EvidenceLevel.LEARNING_TARGET)],
        )

        self.assertEqual(rows[0]["matched_skill_name"], "dbt")

    def test_build_skill_gap_ledger_match_rows_distinguishes_not_in_ledger_from_no_evidence(self):
        rows = self._rows(
            [
                {"term": "GraphQL", "frequency": 1},
                {"term": "Airflow", "frequency": 1},
            ],
            [self._entry("GraphQL", SkillEntry.EvidenceLevel.NO_EVIDENCE)],
        )

        self.assertTrue(rows[0]["is_in_ledger"])
        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.NO_EVIDENCE)
        self.assertFalse(rows[1]["is_in_ledger"])
        self.assertEqual(rows[1]["ledger_status"], "NOT_IN_LEDGER")

    def test_build_skill_gap_ledger_match_rows_preserves_gap_term_order(self):
        rows = self._rows(
            [
                {"term": "Airflow", "frequency": 3},
                {"term": "Python", "frequency": 2},
                {"term": "SQL", "frequency": 1},
            ],
            [
                self._entry("SQL", SkillEntry.EvidenceLevel.VERIFIED),
                self._entry("Python", SkillEntry.EvidenceLevel.VERIFIED),
            ],
        )

        self.assertEqual([row["term"] for row in rows], ["Airflow", "Python", "SQL"])


class SkillGapFailureCountTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="skilluser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="otheruser",
            password="StrongPass12345",
        )

    def _create_app(self, *, user, status, skills_text):
        return JobApplication.objects.create(
            user=user,
            company_name="Co",
            job_title="Analyst",
            date_applied=date(2026, 5, 1),
            status=status,
            required_skills=skills_text,
            job_description="",
        )

    def test_get_global_failure_count_counts_only_rejected_statuses(self):
        self._create_app(
            user=self.user,
            status=ApplicationStatus.REJECTED,
            skills_text="Needs Python and SQL",
        )
        self._create_app(
            user=self.user,
            status=ApplicationStatus.AUTO_REJECTED,
            skills_text="Python required",
        )
        self._create_app(
            user=self.user,
            status=ApplicationStatus.SUBMITTED,
            skills_text="Python",
        )
        self._create_app(
            user=self.user,
            status=ApplicationStatus.INTERVIEW,
            skills_text="Python",
        )
        self._create_app(
            user=self.user,
            status=ApplicationStatus.OFFER,
            skills_text="Python",
        )
        self.assertEqual(get_global_failure_count(user=self.user, skill_name="Python"), 2)

    def test_get_global_failure_count_is_user_scoped(self):
        self._create_app(
            user=self.user,
            status=ApplicationStatus.REJECTED,
            skills_text="Python",
        )
        self._create_app(
            user=self.other_user,
            status=ApplicationStatus.REJECTED,
            skills_text="Python",
        )
        self.assertEqual(get_global_failure_count(user=self.user, skill_name="Python"), 1)
        self.assertEqual(
            get_global_failure_count(user=self.other_user, skill_name="Python"),
            1,
        )

    def test_failure_status_constants_match_evidence_only(self):
        self.assertEqual(
            FAILURE_STATUSES,
            (ApplicationStatus.REJECTED, ApplicationStatus.AUTO_REJECTED),
        )


class SkillGapServiceMutationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="gapuser", password="StrongPass12345")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Beta",
            job_title="BI Analyst",
            date_applied=date(2026, 5, 12),
            status=ApplicationStatus.REJECTED,
            required_skills="Power BI",
            job_description="Dashboard reporting",
        )

    def test_create_or_update_gap_creates_then_updates_safely(self):
        first = create_or_update_gap(
            application=self.application,
            skill_name="Power BI",
            stage=SkillGapStage.APPLICATION,
            current_tier=SkillTier.MISSING,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            long_term_goal=SkillGapLongTermGoal.BI_ANALYST,
            suggested_action="Review portfolio dashboard evidence manually.",
        )
        self.assertTrue(first.created)
        self.assertEqual(first.gap.failure_count, 1)
        self.assertEqual(first.gap.priority, SkillGapPriority.LOW)

        second = create_or_update_gap(
            application=self.application,
            skill_name="Power BI",
            stage=SkillGapStage.APPLICATION,
            current_tier=SkillTier.PRACTICING,
            identified_by=SkillGapIdentifiedBy.RULE_BASED,
            long_term_goal=SkillGapLongTermGoal.BI_ANALYST,
            suggested_action="Updated manual review note.",
        )
        self.assertFalse(second.created)
        self.assertEqual(ApplicationSkillGap.objects.count(), 1)
        self.assertEqual(second.gap.current_tier, SkillTier.PRACTICING)
        self.assertEqual(second.gap.suggested_action, "Updated manual review note.")

    def test_mark_gap_resolved_sets_fields(self):
        result = create_or_update_gap(
            application=self.application,
            skill_name="SQL",
            stage=SkillGapStage.SCREENING,
            current_tier=SkillTier.EMERGING,
            identified_by=SkillGapIdentifiedBy.MANUAL,
        )
        resolved = mark_gap_resolved(
            result.gap,
            resolved_tier=SkillTier.DEMONSTRATED,
            resolved_date=date(2026, 5, 20),
        )
        self.assertTrue(resolved.resolved)
        self.assertEqual(resolved.resolved_date, date(2026, 5, 20))
        self.assertEqual(resolved.resolved_tier, SkillTier.DEMONSTRATED)


class SkillGapSprint43GuardTests(TestCase):
    def test_no_sprint_44_text_in_skill_gaps_core_modules(self):
        scanned_paths = (
            REPO_ROOT / "apps" / "skill_gaps" / "models.py",
            REPO_ROOT / "apps" / "skill_gaps" / "services.py",
            REPO_ROOT / "apps" / "skill_gaps" / "admin.py",
            REPO_ROOT / "apps" / "skill_gaps" / "apps.py",
            REPO_ROOT / "apps" / "skill_gaps" / "migrations" / "0001_initial.py",
        )
        for path in scanned_paths:
            content = path.read_text(encoding="utf-8")
            self.assertNotIn("Sprint 44", content, msg=str(path))

    def test_services_avoid_forbidden_claim_language(self):
        services_content = (REPO_ROOT / "apps" / "skill_gaps" / "services.py").read_text(
            encoding="utf-8"
        )
        lowered = services_content.lower()
        for forbidden in (
            "auto-apply",
            "auto-send",
            "gmail",
            "oauth",
            "scraping",
            "predictive ai",
            "machine learning",
            "live saas",
            "production deployment",
        ):
            with self.subTest(term=forbidden):
                self.assertNotIn(forbidden, lowered)


class SkillGapDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="dashuser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="otherdash",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:dashboard")
        self.app = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.other_app = JobApplication.objects.create(
            user=self.other_user,
            company_name="Other Co",
            job_title="BI Analyst",
            date_applied=date(2026, 5, 11),
        )

    def _login(self):
        self.client.login(username="dashuser", password="StrongPass12345")

    def _create_skill_entry(self, **overrides):
        defaults = {
            "skill_name": "Python",
            "category": SkillEntry.Category.PROGRAMMING,
            "evidence_level": SkillEntry.EvidenceLevel.VERIFIED,
            "sprint_reference": "Sprint 76",
            "project_link": "https://example.com/project",
            "notes": "Private evidence note.",
            "visibility": SkillEntry.Visibility.PRIVATE,
        }
        defaults.update(overrides)
        return SkillEntry.objects.create(**defaults)

    def _create_gap(
        self,
        *,
        application,
        skill_name,
        priority,
        resolved=False,
        stage=SkillGapStage.APPLICATION,
    ):
        score = Decimal("6.00") if priority == SkillGapPriority.HIGH else Decimal("1.00")
        return ApplicationSkillGap.objects.create(
            application=application,
            stage=stage,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=score,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            resolved=resolved,
        )

    def _create_evidence_filter_rows(self):
        for skill_name in (
            "Python",
            "Snowflake",
            "Statistics",
            "GraphQL",
            "Airflow",
        ):
            self._create_gap(
                application=self.app,
                skill_name=skill_name,
                priority=SkillGapPriority.LOW,
            )
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._create_skill_entry(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        self._create_skill_entry(
            skill_name="Statistics",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        self._create_skill_entry(
            skill_name="GraphQL",
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )

    def _response_row_terms(self, response):
        return {
            row["term"]
            for row in response.context["skill_gap_ledger_match_rows"]
        }

    def test_dashboard_requires_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_authenticated_user_can_access_dashboard(self):
        self._login()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skill Intelligence Dashboard")
        self.assertContains(response, "Advisory only")

    def test_dashboard_shows_only_current_user_skill_gaps(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._create_gap(
            application=self.other_app,
            skill_name="Tableau",
            priority=SkillGapPriority.CRITICAL,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Python")
        self.assertNotContains(response, "Tableau")
        self.assertNotContains(response, "Other Co")

    def test_empty_state_when_no_skill_gaps(self):
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "No saved skill gaps to show")

    def test_summary_counts_are_correct(self):
        self._create_gap(application=self.app, skill_name="SQL", priority=SkillGapPriority.HIGH)
        self._create_gap(
            application=self.app,
            skill_name="Excel",
            priority=SkillGapPriority.LOW,
            resolved=True,
        )
        self._create_gap(
            application=self.app,
            skill_name="dbt",
            priority=SkillGapPriority.CRITICAL,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Total saved skill gaps")
        self.assertContains(response, "Unresolved")
        self.assertContains(response, "Resolved")
        self.assertContains(response, "High-priority gaps")
        context = build_skill_gap_dashboard_context(user=self.user, query_params={})
        self.assertEqual(context.summary.total, 3)
        self.assertEqual(context.summary.unresolved, 2)
        self.assertEqual(context.summary.resolved, 1)
        self.assertEqual(context.summary.high_priority, 2)

    def test_priority_filter_works(self):
        self._create_gap(
            application=self.app,
            skill_name="HighOnlySkill",
            priority=SkillGapPriority.HIGH,
        )
        self._create_gap(
            application=self.app,
            skill_name="LowOnlySkill",
            priority=SkillGapPriority.LOW,
        )
        self._login()
        response = self.client.get(self.url, {"priority": SkillGapPriority.HIGH})
        content = response.content.decode()
        self.assertIn("<td><strong>HighOnlySkill</strong></td>", content)
        self.assertNotIn("<td><strong>LowOnlySkill</strong></td>", content)

    def test_stage_filter_works(self):
        self._create_gap(
            application=self.app,
            skill_name="ScreenStageSkill",
            priority=SkillGapPriority.MEDIUM,
            stage=SkillGapStage.SCREENING,
        )
        self._create_gap(
            application=self.app,
            skill_name="AppStageSkill",
            priority=SkillGapPriority.MEDIUM,
            stage=SkillGapStage.APPLICATION,
        )
        self._login()
        response = self.client.get(self.url, {"stage": SkillGapStage.SCREENING})
        content = response.content.decode()
        self.assertIn("<td><strong>ScreenStageSkill</strong></td>", content)
        self.assertNotIn("<td><strong>AppStageSkill</strong></td>", content)

    def test_resolved_filter_works(self):
        self._create_gap(
            application=self.app,
            skill_name="Open skill",
            priority=SkillGapPriority.LOW,
        )
        self._create_gap(
            application=self.app,
            skill_name="Closed skill",
            priority=SkillGapPriority.LOW,
            resolved=True,
        )
        self._login()
        response = self.client.get(self.url, {"resolved": "yes"})
        content = response.content.decode()
        self.assertIn("<td><strong>Closed skill</strong></td>", content)
        self.assertNotIn("<td><strong>Open skill</strong></td>", content)

    def test_dashboard_evidence_filter_defaults_to_all(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.context["evidence_filter"], "all")
        self.assertEqual(
            self._response_row_terms(response),
            {"Python", "Snowflake", "Statistics", "GraphQL", "Airflow"},
        )

    def test_dashboard_evidence_filter_invalid_value_falls_back_to_all(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "external_verified"})

        self.assertEqual(response.context["evidence_filter"], "all")
        self.assertEqual(
            self._response_row_terms(response),
            {"Python", "Snowflake", "Statistics", "GraphQL", "Airflow"},
        )

    def test_dashboard_evidence_filter_verified_only(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "verified"})

        self.assertEqual(self._response_row_terms(response), {"Python"})
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.VERIFIED)

    def test_dashboard_evidence_filter_learning_target_only(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "learning_target"})

        self.assertEqual(self._response_row_terms(response), {"Snowflake"})
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(
            rows[0]["ledger_status"],
            SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )

    def test_dashboard_evidence_filter_studying_only(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "studying"})

        self.assertEqual(self._response_row_terms(response), {"Statistics"})
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.STUDYING)

    def test_dashboard_evidence_filter_no_evidence_only(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "no_evidence"})

        self.assertEqual(self._response_row_terms(response), {"GraphQL"})
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.NO_EVIDENCE)

    def test_dashboard_evidence_filter_not_in_ledger_only(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "not_in_ledger"})

        self.assertEqual(self._response_row_terms(response), {"Airflow"})
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(rows[0]["ledger_status"], "NOT_IN_LEDGER")

    def test_dashboard_evidence_filter_needs_evidence_combines_no_evidence_and_not_in_ledger(
        self,
    ):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "needs_evidence"})

        self.assertEqual(self._response_row_terms(response), {"GraphQL", "Airflow"})
        statuses = {
            row["ledger_status"]
            for row in response.context["skill_gap_ledger_match_rows"]
        }
        self.assertEqual(
            statuses,
            {SkillEntry.EvidenceLevel.NO_EVIDENCE, "NOT_IN_LEDGER"},
        )

    def test_dashboard_evidence_filter_preserves_matched_skill_name(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "verified"})

        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(rows[0]["matched_skill_name"], "Python")
        self.assertContains(response, "Matched Skill Ledger skill: Python")

    def test_dashboard_evidence_filter_is_read_only(self):
        self._create_evidence_filter_rows()
        skill_entry_count = SkillEntry.objects.count()
        skill_gap_count = ApplicationSkillGap.objects.count()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "needs_evidence"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SkillEntry.objects.count(), skill_entry_count)
        self.assertEqual(ApplicationSkillGap.objects.count(), skill_gap_count)

    def test_dashboard_evidence_filter_renders_safety_wording(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "no_evidence"})

        self.assertContains(
            response,
            (
                "Gap signals are advisory only. Skill Ledger status reflects your own manually "
                "maintained records. A VERIFIED status means portfolio evidence exists - it does "
                "not mean you meet any employer requirement. This table does not score "
                "suitability, verify proficiency, or create Skill Ledger entries. Use human "
                "judgement before claiming a skill against a specific role."
            ),
        )

    def test_dashboard_evidence_filter_control_renders_selected_option(self):
        self._create_evidence_filter_rows()
        self._login()

        response = self.client.get(self.url, {"evidence_filter": "studying"})

        self.assertContains(response, 'name="evidence_filter"')
        self.assertContains(response, "All Skill Ledger statuses")
        self.assertContains(response, "Needs evidence")
        self.assertContains(
            response,
            '<option value="studying" selected>STUDYING</option>',
        )

    def test_dashboard_is_read_only(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.LOW)
        self._login()
        get_response = self.client.get(self.url)
        self.assertEqual(get_response.status_code, 200)
        post_response = self.client.post(self.url, {"skill_name": "Hack"})
        self.assertEqual(post_response.status_code, 405)
        self.assertEqual(ApplicationSkillGap.objects.count(), 1)

    def test_build_skill_gap_dashboard_context_scopes_by_user(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.LOW)
        self._create_gap(
            application=self.other_app,
            skill_name="Hidden",
            priority=SkillGapPriority.LOW,
        )
        context = build_skill_gap_dashboard_context(user=self.user, query_params={})
        self.assertEqual(context.summary.total, 1)
        self.assertEqual(len(context.gaps), 1)
        self.assertEqual(context.gaps[0].skill_name, "Python")

    def test_no_model_changes_or_migrations_added(self):
        migration_dir = REPO_ROOT / "apps" / "skill_gaps" / "migrations"
        migration_files = [
            path.name
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]
        self.assertEqual(migration_files, ["0001_initial.py"])

    def test_no_sprint_52_text_on_dashboard_page(self):
        self._login()
        response = self.client.get(self.url)
        self.assertNotContains(response, "Sprint 52")

    def test_dashboard_avoids_forbidden_claim_language(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("advisory only", content)
        self.assertIn("manually saved", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("predictive ai", content)
        self.assertNotIn("gmail", content)
        self.assertNotIn("live saas users", content)

    def test_sprint_69g_dashboard_premium_shell_renders(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Skill Intelligence Dashboard")
        expected_classes = [
            "cf69g-page",
            "cf69g-hero",
            "cf69g-safety-note",
            "cf69g-kpi-grid",
            "cf69g-kpi-card",
            "cf69g-section",
            "cf69g-filter-bar",
        ]
        for class_name in expected_classes:
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_skill_gaps_dashboard_includes_skill_ledger_summary_context(self):
        self._create_skill_entry()
        self._login()

        response = self.client.get(self.url)

        self.assertIn("skill_ledger_summary", response.context)
        self.assertEqual(response.context["skill_ledger_summary"]["total_entries"], 1)

    def test_skill_gaps_dashboard_renders_skill_ledger_evidence_summary_section(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Skill Ledger Evidence Summary")

    def test_skill_gaps_dashboard_renders_verified_count(self):
        self._create_skill_entry(evidence_level=SkillEntry.EvidenceLevel.VERIFIED)
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "VERIFIED")
        self.assertContains(response, "Python")
        self.assertEqual(
            response.context["skill_ledger_summary"]["counts"][SkillEntry.EvidenceLevel.VERIFIED],
            1,
        )

    def test_skill_gaps_dashboard_renders_learning_target_count(self):
        self._create_skill_entry(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "LEARNING_TARGET")
        self.assertEqual(
            response.context["skill_ledger_summary"]["counts"][
                SkillEntry.EvidenceLevel.LEARNING_TARGET
            ],
            1,
        )

    def test_skill_gaps_dashboard_renders_studying_count(self):
        self._create_skill_entry(
            skill_name="Statistics",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "STUDYING")
        self.assertEqual(
            response.context["skill_ledger_summary"]["counts"][SkillEntry.EvidenceLevel.STUDYING],
            1,
        )

    def test_skill_gaps_dashboard_renders_no_evidence_count(self):
        self._create_skill_entry(
            skill_name="GraphQL",
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "NO_EVIDENCE")
        self.assertEqual(
            response.context["skill_ledger_summary"]["counts"][
                SkillEntry.EvidenceLevel.NO_EVIDENCE
            ],
            1,
        )

    def test_skill_gaps_dashboard_renders_private_skill_ledger_link(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, reverse("skill_ledger:list"))
        self.assertContains(response, "Open private Skill Ledger")

    def test_skill_gaps_dashboard_skill_ledger_advisory_wording_present(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            (
                "Skill Ledger evidence is manually maintained and supports portfolio planning. "
                "It does not verify a skill by itself."
            ),
        )

    def test_skill_gaps_dashboard_verified_boundary_wording_present(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            (
                "VERIFIED means portfolio evidence exists in a closed sprint, passing tests, "
                "or prior work experience - not external certification."
            ),
        )

    def test_skill_gaps_dashboard_read_only_note_present(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            "This summary is read-only. To update your Skill Ledger, use the private Skill Ledger.",
        )

    def test_skill_gaps_dashboard_renders_empty_state_when_no_entries(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No Skill Ledger entries recorded yet.")

    def test_skill_gaps_dashboard_renders_empty_state_when_no_verified_entries(self):
        self._create_skill_entry(
            skill_name="Snowflake",
            evidence_level=SkillEntry.EvidenceLevel.LEARNING_TARGET,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No VERIFIED Skill Ledger entries recorded yet.")

    def test_skill_gaps_dashboard_does_not_imply_automatic_verification(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        for phrase in (
            "automatic verification",
            "automatic skill syncing",
            "ai scoring",
            "ml scoring",
            "job-fit scoring",
            "auto-apply",
            "scraping",
            "background task processing",
            "guaranteed readiness",
            "verified skill mastery",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_skill_gaps_dashboard_does_not_imply_employer_confirmation_or_certification(
        self,
    ):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        for phrase in (
            "employer verification",
            "employer confirmation",
            "cert" + "ified",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_skill_gaps_dashboard_preserves_existing_skill_gap_heading(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Skill Intelligence Dashboard")
        self.assertContains(response, "Application skill gaps")

    def test_skill_gaps_dashboard_preserves_existing_advisory_only_wording(self):
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            "Advisory only. This read-only view surfaces manually saved application skill-gap",
        )
        self.assertContains(response, "Based on manually saved application skill-gap records")

    def test_skill_gaps_dashboard_get_does_not_mutate_skill_ledger_entries(self):
        entry = self._create_skill_entry(
            skill_name="Power BI",
            evidence_level=SkillEntry.EvidenceLevel.STUDYING,
        )
        before = SkillEntry.objects.values(
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
            "last_updated",
        ).get(pk=entry.pk)
        self._login()

        response = self.client.get(self.url)

        after = SkillEntry.objects.values(
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
            "last_updated",
        ).get(pk=entry.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(after, before)

    def test_skill_gaps_dashboard_preserves_existing_saved_gap_records(self):
        self._create_gap(
            application=self.app,
            skill_name="Power BI",
            priority=SkillGapPriority.HIGH,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Power BI")
        self.assertContains(response, "Acme")
        self.assertContains(response, "Data Analyst")

    def test_skill_gaps_dashboard_preserves_existing_cf69g_classes(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode()

        for class_name in (
            "cf69g-page",
            "cf69g-hero",
            "cf69g-safety-note",
            "cf69g-kpi-grid",
            "cf69g-kpi-card",
            "cf69g-section",
            "cf69g-filter-bar",
            "cf69g-table-wrap",
            "cf69g-empty-state",
        ):
            with self.subTest(class_name=class_name):
                self.assertIn(class_name, content)

    def test_skill_gaps_dashboard_does_not_match_individual_gaps_to_ledger_entries(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertContains(response, "Python")
        self.assertNotIn("ledger match", content)
        self.assertNotIn("gap-to-ledger", content)

    def test_dashboard_includes_skill_gap_ledger_match_rows_context(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertIn("skill_gap_ledger_match_rows", response.context)
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["term"], "Python")
        self.assertEqual(rows[0]["ledger_status"], SkillEntry.EvidenceLevel.VERIFIED)

    def test_dashboard_renders_skill_ledger_status_column(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Skill Ledger Status")

    def test_dashboard_renders_verified_skill_ledger_status(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "VERIFIED")
        self.assertContains(response, "Matched Skill Ledger skill: Python")

    def test_dashboard_renders_not_in_skill_ledger_status(self):
        self._create_gap(application=self.app, skill_name="Airflow", priority=SkillGapPriority.LOW)
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Not in Skill Ledger")
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertFalse(rows[0]["is_in_ledger"])

    def test_dashboard_renders_gap_ledger_matching_safety_wording(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            (
                "Gap signals are advisory only. Skill Ledger status reflects your own manually "
                "maintained records. A VERIFIED status means portfolio evidence exists - it does "
                "not mean you meet any employer requirement. This table does not score "
                "suitability, verify proficiency, or create Skill Ledger entries. Use human "
                "judgement before claiming a skill against a specific role."
            ),
        )

    def test_dashboard_preserves_existing_skill_gap_table_content(self):
        self._create_gap(
            application=self.app,
            skill_name="Power BI",
            priority=SkillGapPriority.HIGH,
            stage=SkillGapStage.TECHNICAL,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Power BI")
        self.assertContains(response, "Acme")
        self.assertContains(response, "Data Analyst")
        self.assertContains(response, "Technical")
        self.assertContains(response, "Priority score")
        self.assertContains(response, "Suggested action")

    def test_dashboard_preserves_sprint_77_skill_ledger_summary(self):
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Skill Ledger Evidence Summary")
        self.assertContains(
            response,
            (
                "Skill Ledger evidence is manually maintained and supports portfolio planning. "
                "It does not verify a skill by itself."
            ),
        )
        self.assertContains(response, "Open private Skill Ledger")

    def test_dashboard_gap_ledger_matching_empty_state_when_no_gap_terms_exist(self):
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No saved skill gaps to show.")
        self.assertEqual(response.context["skill_gap_ledger_match_rows"], ())

    def test_dashboard_gap_ledger_matching_handles_empty_skill_ledger(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            (
                "Your Skill Ledger has no entries yet. Matching is read-only and does not "
                "create Skill Ledger records."
            ),
        )
        self.assertContains(response, "Not in Skill Ledger")

    def test_dashboard_gap_ledger_matching_does_not_imply_employer_requirement_met(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertIn("does not mean you meet any employer requirement", content)
        for phrase in (
            "employer-ready",
            "guaranteed readiness",
            "verified skill mastery",
            "meets employer requirements",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_dashboard_gap_ledger_matching_does_not_mutate_skill_ledger_entries(self):
        entry = self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        before = SkillEntry.objects.values(
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
            "last_updated",
        ).get(pk=entry.pk)
        self._login()

        response = self.client.get(self.url)

        after = SkillEntry.objects.values(
            "skill_name",
            "category",
            "evidence_level",
            "sprint_reference",
            "project_link",
            "notes",
            "visibility",
            "last_updated",
        ).get(pk=entry.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(after, before)

    def test_dashboard_gap_ledger_matching_does_not_mutate_skill_gap_records(self):
        gap = self._create_gap(
            application=self.app,
            skill_name="Python",
            priority=SkillGapPriority.HIGH,
        )
        self._create_skill_entry(
            skill_name="Python",
            evidence_level=SkillEntry.EvidenceLevel.VERIFIED,
        )
        before = ApplicationSkillGap.objects.values(
            "skill_name",
            "priority",
            "priority_score",
            "resolved",
            "suggested_action",
        ).get(pk=gap.pk)
        self._login()

        response = self.client.get(self.url)

        after = ApplicationSkillGap.objects.values(
            "skill_name",
            "priority",
            "priority_score",
            "resolved",
            "suggested_action",
        ).get(pk=gap.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(after, before)

    def test_dashboard_gap_ledger_matching_does_not_create_skill_ledger_entries(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        before = SkillEntry.objects.count()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(SkillEntry.objects.count(), before)

    def test_dashboard_renders_matched_skill_name_for_alias_match(self):
        self._create_gap(
            application=self.app,
            skill_name="SQL Server",
            priority=SkillGapPriority.HIGH,
        )
        self._create_skill_entry(skill_name="SQL", evidence_level=SkillEntry.EvidenceLevel.VERIFIED)
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "<td><strong>SQL Server</strong></td>", html=True)
        self.assertContains(response, "Matched Skill Ledger skill: SQL")
        rows = response.context["skill_gap_ledger_match_rows"]
        self.assertEqual(rows[0]["term"], "SQL Server")
        self.assertEqual(rows[0]["matched_skill_name"], "SQL")

    def test_dashboard_distinguishes_not_in_ledger_from_no_evidence(self):
        self._create_gap(
            application=self.app,
            skill_name="GraphQL",
            priority=SkillGapPriority.LOW,
        )
        self._create_gap(application=self.app, skill_name="Airflow", priority=SkillGapPriority.LOW)
        self._create_skill_entry(
            skill_name="GraphQL",
            evidence_level=SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        self._login()

        response = self.client.get(self.url)
        rows_by_term = {
            row["term"]: row for row in response.context["skill_gap_ledger_match_rows"]
        }

        self.assertContains(response, "NO_EVIDENCE")
        self.assertContains(response, "Not in Skill Ledger")
        self.assertTrue(rows_by_term["GraphQL"]["is_in_ledger"])
        self.assertEqual(
            rows_by_term["GraphQL"]["ledger_status"],
            SkillEntry.EvidenceLevel.NO_EVIDENCE,
        )
        self.assertFalse(rows_by_term["Airflow"]["is_in_ledger"])

    def test_dashboard_preserves_cf69g_table_wrapper_class(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "cf69g-table-wrap")

    def test_dashboard_does_not_render_ai_or_scoring_claims(self):
        self._create_gap(application=self.app, skill_name="Python", priority=SkillGapPriority.HIGH)
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode().lower()

        for phrase in (
            "ai scored",
            "ai scoring",
            "job-fit scoring",
            "automatically verified",
            "meets employer requirements",
            "employer-ready",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_sprint_69g_dashboard_preserves_manual_advisory_read_only_framing(self):
        self._login()
        response = self.client.get(self.url)

        self.assertContains(response, "Advisory only")
        self.assertContains(response, "read-only view")
        self.assertContains(response, "manually saved application skill-gap records")
        self.assertContains(response, "Evidence-informed planning")
        self.assertContains(response, "not automatic profile changes")
        self.assertContains(response, "does not create, update, or delete gaps automatically")

    def test_sprint_69g_saved_gap_records_still_render_in_polished_table(self):
        self._create_gap(
            application=self.app,
            skill_name="Power BI",
            priority=SkillGapPriority.HIGH,
            stage=SkillGapStage.TECHNICAL,
        )
        self._login()
        response = self.client.get(self.url)

        self.assertContains(response, "Application skill gaps")
        self.assertContains(response, "Power BI")
        self.assertContains(response, "Acme")
        self.assertContains(response, "Data Analyst")
        self.assertContains(response, "cf69g-table-wrap")

    def test_sprint_69g_empty_state_remains_safe_and_scoped(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertContains(response, "No saved skill gaps to show")
        self.assertContains(response, "This dashboard does not create gaps automatically")
        self.assertIn("cf69g-empty-state", content)
        self.assertNotContains(response, "guaranteed readiness")
        self.assertNotContains(response, "verified skill mastery")

    def test_sprint_69g_learning_targets_are_manual_evidence_review_items(self):
        for skill_name in ("dbt", "Airflow", "Snowflake", "BigQuery", "Power BI"):
            self._create_gap(
                application=self.app,
                skill_name=skill_name,
                priority=SkillGapPriority.LOW,
            )
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        for skill_name in ("dbt", "airflow", "snowflake", "bigquery", "power bi"):
            with self.subTest(skill_name=skill_name):
                self.assertIn(skill_name, content)
        self.assertContains(response, "Manual evidence review before claiming")
        forbidden_phrases = [
            "verified skill mastery",
            "guaranteed readiness",
            "proven current skills",
            "employer verification",
            "external verification",
            "hiring prediction",
            "automatic career decisioning",
        ]
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_sprint_69g_dashboard_does_not_imply_automatic_cv_or_profile_changes(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertIn("not hiring decisions or automatic cv changes", content)
        self.assertIn("not automatic profile changes", content)
        forbidden_phrases = [
            "updates your cv automatically",
            "automatic profile updates",
            "rewrites your cv automatically",
            "publishes profile changes",
        ]
        for phrase in forbidden_phrases:
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_sprint_69g_dashboard_get_does_not_create_update_or_delete_gap_records(self):
        gap = self._create_gap(
            application=self.app,
            skill_name="SQL",
            priority=SkillGapPriority.HIGH,
        )
        before = list(
            ApplicationSkillGap.objects.filter(application__user=self.user).values(
                "pk",
                "skill_name",
                "priority",
                "resolved",
                "priority_score",
                "updated_at",
            )
        )

        self._login()
        response = self.client.get(self.url, {"priority": SkillGapPriority.HIGH})
        gap.refresh_from_db()
        after = list(
            ApplicationSkillGap.objects.filter(application__user=self.user).values(
                "pk",
                "skill_name",
                "priority",
                "resolved",
                "priority_score",
                "updated_at",
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(before, after)
        self.assertEqual(gap.skill_name, "SQL")

    def test_sprint_69g_dashboard_template_keeps_styles_page_scoped(self):
        template_path = REPO_ROOT / "templates" / "skill_gaps" / "dashboard.html"
        template_source = template_path.read_text(encoding="utf-8")

        self.assertIn("cf69g-", template_source)
        self.assertIn("<style>", template_source)
        self.assertNotIn("static/css", template_source)
        self.assertNotIn("static/js", template_source)


class SkillGapActionPlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="planuser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="planother",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:dashboard")
        self.app = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.other_app = JobApplication.objects.create(
            user=self.other_user,
            company_name="Rival",
            job_title="Engineer",
            date_applied=date(2026, 5, 11),
        )

    def _login(self):
        self.client.login(username="planuser", password="StrongPass12345")

    def _create_gap(
        self,
        *,
        application,
        skill_name,
        priority,
        priority_score,
        resolved=False,
    ):
        return ApplicationSkillGap.objects.create(
            application=application,
            stage=SkillGapStage.APPLICATION,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=priority_score,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            suggested_action=f"Review {skill_name} manually.",
            resolved=resolved,
        )

    def test_action_plan_section_appears_on_dashboard(self):
        self._create_gap(
            application=self.app,
            skill_name="Python",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("8.00"),
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Manual action plan")
        self.assertContains(response, "Suggested next steps")
        self.assertContains(response, "Review and decide manually")

    def test_action_plan_context_is_user_scoped(self):
        self._create_gap(
            application=self.app,
            skill_name="SQL",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
        )
        self._create_gap(
            application=self.other_app,
            skill_name="HiddenSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        plan = build_skill_gap_action_plan_context(user=self.user)
        names = {
            gap.skill_name
            for group in (
                plan.high_priority_unresolved,
                plan.medium_priority_unresolved,
                plan.lower_priority_backlog,
            )
            for gap in group.items
        }
        self.assertIn("SQL", names)
        self.assertNotIn("HiddenSkill", names)

    def test_high_priority_unresolved_appear_before_lower_priority(self):
        self._create_gap(
            application=self.app,
            skill_name="LowSkill",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="CriticalSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        plan = build_skill_gap_action_plan_context(user=self.user)
        self.assertEqual(plan.high_priority_unresolved.items[0].skill_name, "CriticalSkill")
        self.assertEqual(plan.lower_priority_backlog.items[0].skill_name, "LowSkill")

    def test_resolved_gaps_not_in_primary_next_actions(self):
        self._create_gap(
            application=self.app,
            skill_name="OpenGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("7.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="DoneGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
            resolved=True,
        )
        plan = build_skill_gap_action_plan_context(user=self.user)
        primary_names = [gap.skill_name for gap in plan.high_priority_unresolved.items]
        primary_names += [gap.skill_name for gap in plan.medium_priority_unresolved.items]
        primary_names += [gap.skill_name for gap in plan.lower_priority_backlog.items]
        self.assertEqual(primary_names, ["OpenGap"])
        self.assertEqual(plan.resolved_context.items[0].skill_name, "DoneGap")

    def test_empty_action_plan_when_no_unresolved_gaps(self):
        self._create_gap(
            application=self.app,
            skill_name="DoneOnly",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
            resolved=True,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "No unresolved skill gaps for a manual action plan")
        plan = build_skill_gap_action_plan_context(user=self.user)
        self.assertFalse(plan.has_unresolved)

    def test_dashboard_get_does_not_mutate_skill_gaps(self):
        self._create_gap(
            application=self.app,
            skill_name="Stable",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("3.00"),
        )
        self._login()
        before = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        after = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        self.assertEqual(before, after)

    def test_get_action_plan_items_returns_only_unresolved_ordered(self):
        self._create_gap(
            application=self.app,
            skill_name="A",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="B",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="C",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
            resolved=True,
        )
        items = get_action_plan_items(user=self.user)
        self.assertEqual([gap.skill_name for gap in items], ["B", "A"])

    def test_action_plan_avoids_forbidden_claim_language(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("manual action plan", content)
        self.assertIn("advisory only", content)
        self.assertIn("based on saved skill-gap records", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("predictive ai", content)
        self.assertNotIn("gmail", content)


class SkillGapLearningPlanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="learnuser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="learnother",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:dashboard")
        self.app = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.other_app = JobApplication.objects.create(
            user=self.other_user,
            company_name="Rival",
            job_title="Engineer",
            date_applied=date(2026, 5, 11),
        )

    def _login(self):
        self.client.login(username="learnuser", password="StrongPass12345")

    def _create_gap(
        self,
        *,
        application,
        skill_name,
        priority,
        priority_score,
        resolved=False,
    ):
        return ApplicationSkillGap.objects.create(
            application=application,
            stage=SkillGapStage.APPLICATION,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=priority_score,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            suggested_action=f"Practice {skill_name} manually.",
            resolved=resolved,
        )

    def test_learning_plan_section_appears_on_dashboard(self):
        self._create_gap(
            application=self.app,
            skill_name="Python",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("8.00"),
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Manual learning plan")
        self.assertContains(response, "Learning focus")
        self.assertContains(response, "Suggested practice")
        self.assertContains(response, "Review and decide manually")

    def test_learning_plan_context_is_user_scoped(self):
        self._create_gap(
            application=self.app,
            skill_name="SQL",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
        )
        self._create_gap(
            application=self.other_app,
            skill_name="HiddenSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        plan = build_skill_gap_learning_plan_context(user=self.user)
        names = {
            gap.skill_name
            for group in (
                plan.immediate_learning_focus,
                plan.practice_next,
                plan.backlog_learning_items,
            )
            for gap in group.items
        }
        self.assertIn("SQL", names)
        self.assertNotIn("HiddenSkill", names)

    def test_high_priority_unresolved_appear_before_backlog_learning_items(self):
        self._create_gap(
            application=self.app,
            skill_name="LowSkill",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="CriticalSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        plan = build_skill_gap_learning_plan_context(user=self.user)
        self.assertEqual(
            plan.immediate_learning_focus.items[0].skill_name,
            "CriticalSkill",
        )
        self.assertEqual(
            plan.backlog_learning_items.items[0].skill_name,
            "LowSkill",
        )

    def test_resolved_gaps_not_in_primary_learning_focus(self):
        self._create_gap(
            application=self.app,
            skill_name="OpenGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("7.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="DoneGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
            resolved=True,
        )
        plan = build_skill_gap_learning_plan_context(user=self.user)
        primary_names = [
            gap.skill_name for gap in plan.immediate_learning_focus.items
        ]
        primary_names += [gap.skill_name for gap in plan.practice_next.items]
        primary_names += [gap.skill_name for gap in plan.backlog_learning_items.items]
        self.assertEqual(primary_names, ["OpenGap"])
        self.assertEqual(plan.resolved_learning_context.items[0].skill_name, "DoneGap")

    def test_empty_learning_plan_when_no_unresolved_gaps(self):
        self._create_gap(
            application=self.app,
            skill_name="DoneOnly",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
            resolved=True,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "No unresolved skill gaps for a manual learning plan")
        plan = build_skill_gap_learning_plan_context(user=self.user)
        self.assertFalse(plan.has_unresolved)

    def test_dashboard_get_does_not_mutate_skill_gaps_for_learning_plan(self):
        self._create_gap(
            application=self.app,
            skill_name="Stable",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("3.00"),
        )
        self._login()
        before = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        after = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        self.assertEqual(before, after)

    def test_get_learning_plan_items_returns_only_unresolved_ordered(self):
        self._create_gap(
            application=self.app,
            skill_name="A",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="B",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="C",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
            resolved=True,
        )
        items = get_learning_plan_items(user=self.user)
        self.assertEqual([gap.skill_name for gap in items], ["B", "A"])

    def test_learning_plan_avoids_forbidden_claim_language(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("manual learning plan", content)
        self.assertIn("advisory only", content)
        self.assertIn("based on saved skill-gap records", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("predictive ai", content)
        self.assertNotIn("gmail", content)
        self.assertNotIn("sprint 48", content)

    def test_no_model_changes_or_migrations_added(self):
        migration_dir = REPO_ROOT / "apps" / "skill_gaps" / "migrations"
        migration_files = [
            path.name
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]
        self.assertEqual(migration_files, ["0001_initial.py"])

    def test_sprint_46_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "apps" / "skill_gaps" / "services.py",
            REPO_ROOT / "apps" / "skill_gaps" / "views.py",
            REPO_ROOT / "apps" / "skill_gaps" / "tests.py",
            REPO_ROOT / "templates" / "skill_gaps" / "dashboard.html",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )


class SkillGapEvidenceReadinessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="eviduser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="evidother",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:dashboard")
        self.app = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.other_app = JobApplication.objects.create(
            user=self.other_user,
            company_name="Rival",
            job_title="Engineer",
            date_applied=date(2026, 5, 11),
        )

    def _login(self):
        self.client.login(username="eviduser", password="StrongPass12345")

    def _create_gap(
        self,
        *,
        application,
        skill_name,
        priority,
        priority_score,
        resolved=False,
    ):
        return ApplicationSkillGap.objects.create(
            application=application,
            stage=SkillGapStage.APPLICATION,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=priority_score,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            suggested_action=f"Document {skill_name} evidence manually.",
            resolved=resolved,
        )

    def test_evidence_readiness_section_appears_on_dashboard(self):
        self._create_gap(
            application=self.app,
            skill_name="Python",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("8.00"),
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Manual evidence readiness")
        self.assertContains(response, "Evidence focus")
        self.assertContains(response, "Suggested evidence")
        self.assertContains(response, "Portfolio project evidence")
        self.assertContains(response, "CV bullet evidence")
        self.assertContains(response, "Interview story evidence")
        self.assertContains(response, "Dashboard/reporting evidence")
        self.assertContains(response, "Review and decide manually")

    def test_evidence_readiness_context_is_user_scoped(self):
        self._create_gap(
            application=self.app,
            skill_name="SQL",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
        )
        self._create_gap(
            application=self.other_app,
            skill_name="HiddenSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        plan = build_skill_gap_evidence_readiness_context(user=self.user)
        names = {
            gap.skill_name
            for group in (
                plan.evidence_needed_now,
                plan.strengthen_next,
                plan.evidence_backlog,
            )
            for gap in group.items
        }
        self.assertIn("SQL", names)
        self.assertNotIn("HiddenSkill", names)

    def test_high_priority_unresolved_appear_before_evidence_backlog(self):
        self._create_gap(
            application=self.app,
            skill_name="LowSkill",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="CriticalSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        plan = build_skill_gap_evidence_readiness_context(user=self.user)
        self.assertEqual(plan.evidence_needed_now.items[0].skill_name, "CriticalSkill")
        self.assertEqual(plan.evidence_backlog.items[0].skill_name, "LowSkill")

    def test_resolved_gaps_not_in_primary_evidence_focus(self):
        self._create_gap(
            application=self.app,
            skill_name="OpenGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("7.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="DoneGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
            resolved=True,
        )
        plan = build_skill_gap_evidence_readiness_context(user=self.user)
        primary_names = [gap.skill_name for gap in plan.evidence_needed_now.items]
        primary_names += [gap.skill_name for gap in plan.strengthen_next.items]
        primary_names += [gap.skill_name for gap in plan.evidence_backlog.items]
        self.assertEqual(primary_names, ["OpenGap"])
        self.assertEqual(plan.resolved_evidence_context.items[0].skill_name, "DoneGap")

    def test_empty_evidence_readiness_when_no_unresolved_gaps(self):
        self._create_gap(
            application=self.app,
            skill_name="DoneOnly",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
            resolved=True,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "No unresolved skill gaps for manual evidence readiness")
        plan = build_skill_gap_evidence_readiness_context(user=self.user)
        self.assertFalse(plan.has_unresolved)

    def test_dashboard_get_does_not_mutate_skill_gaps_for_evidence_readiness(self):
        self._create_gap(
            application=self.app,
            skill_name="Stable",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("3.00"),
        )
        self._login()
        before = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        after = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        self.assertEqual(before, after)

    def test_get_evidence_readiness_items_returns_only_unresolved_ordered(self):
        self._create_gap(
            application=self.app,
            skill_name="A",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="B",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="C",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
            resolved=True,
        )
        items = get_evidence_readiness_items(user=self.user)
        self.assertEqual([gap.skill_name for gap in items], ["B", "A"])

    def test_evidence_readiness_avoids_forbidden_claim_language(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("manual evidence readiness", content)
        self.assertIn("advisory only", content)
        self.assertIn("based on saved skill-gap records", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("auto-send", content)
        self.assertNotIn("predictive ai", content)
        self.assertNotIn("gmail", content)
        self.assertNotIn("oauth", content)
        self.assertNotIn("sprint 49", content)

    def test_no_model_changes_or_migrations_added(self):
        migration_dir = REPO_ROOT / "apps" / "skill_gaps" / "migrations"
        migration_files = [
            path.name
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]
        self.assertEqual(migration_files, ["0001_initial.py"])

    def test_sprint_47_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "apps" / "skill_gaps" / "services.py",
            REPO_ROOT / "apps" / "skill_gaps" / "views.py",
            REPO_ROOT / "apps" / "skill_gaps" / "tests.py",
            REPO_ROOT / "templates" / "skill_gaps" / "dashboard.html",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )


class SkillGapPortfolioEvidenceMappingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="portuser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="portother",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:dashboard")
        self.app = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.other_app = JobApplication.objects.create(
            user=self.other_user,
            company_name="Rival",
            job_title="Engineer",
            date_applied=date(2026, 5, 11),
        )

    def _login(self):
        self.client.login(username="portuser", password="StrongPass12345")

    def _create_gap(
        self,
        *,
        application,
        skill_name,
        priority,
        priority_score,
        resolved=False,
    ):
        return ApplicationSkillGap.objects.create(
            application=application,
            stage=SkillGapStage.APPLICATION,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=priority_score,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            suggested_action=f"Map {skill_name} proof manually.",
            resolved=resolved,
        )

    def test_portfolio_evidence_mapping_section_appears_on_dashboard(self):
        self._create_gap(
            application=self.app,
            skill_name="Python",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("8.00"),
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Manual portfolio evidence mapping")
        self.assertContains(response, "Portfolio proof focus")
        self.assertContains(response, "Suggested proof ideas")
        self.assertContains(response, "Portfolio project proof (manual prompt)")
        self.assertContains(response, "CV bullet proof (manual prompt)")
        self.assertContains(response, "Interview story proof (manual prompt)")
        self.assertContains(response, "Dashboard/reporting proof (manual prompt)")
        self.assertContains(response, "Business impact proof (manual prompt)")
        self.assertContains(response, "Review and decide manually")

    def test_portfolio_evidence_mapping_context_is_user_scoped(self):
        self._create_gap(
            application=self.app,
            skill_name="SQL",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
        )
        self._create_gap(
            application=self.other_app,
            skill_name="HiddenSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        mapping = build_skill_gap_portfolio_evidence_mapping_context(user=self.user)
        names = {
            gap.skill_name
            for group in (
                mapping.map_to_portfolio_proof_now,
                mapping.strengthen_cv_interview_evidence_next,
                mapping.evidence_backlog,
            )
            for gap in group.items
        }
        self.assertIn("SQL", names)
        self.assertNotIn("HiddenSkill", names)

    def test_high_priority_unresolved_appear_before_mapping_backlog(self):
        self._create_gap(
            application=self.app,
            skill_name="LowSkill",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="CriticalSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        mapping = build_skill_gap_portfolio_evidence_mapping_context(user=self.user)
        self.assertEqual(
            mapping.map_to_portfolio_proof_now.items[0].skill_name,
            "CriticalSkill",
        )
        self.assertEqual(mapping.evidence_backlog.items[0].skill_name, "LowSkill")

    def test_resolved_gaps_not_in_primary_portfolio_proof_focus(self):
        self._create_gap(
            application=self.app,
            skill_name="OpenGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("7.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="DoneGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
            resolved=True,
        )
        mapping = build_skill_gap_portfolio_evidence_mapping_context(user=self.user)
        primary_names = [
            gap.skill_name for gap in mapping.map_to_portfolio_proof_now.items
        ]
        primary_names += [
            gap.skill_name for gap in mapping.strengthen_cv_interview_evidence_next.items
        ]
        primary_names += [gap.skill_name for gap in mapping.evidence_backlog.items]
        self.assertEqual(primary_names, ["OpenGap"])
        self.assertEqual(
            mapping.resolved_evidence_mapping_context.items[0].skill_name,
            "DoneGap",
        )

    def test_empty_portfolio_evidence_mapping_when_no_unresolved_gaps(self):
        self._create_gap(
            application=self.app,
            skill_name="DoneOnly",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
            resolved=True,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(
            response,
            "No unresolved skill gaps for manual portfolio evidence mapping",
        )
        mapping = build_skill_gap_portfolio_evidence_mapping_context(user=self.user)
        self.assertFalse(mapping.has_unresolved)

    def test_dashboard_get_does_not_mutate_skill_gaps_for_portfolio_mapping(self):
        self._create_gap(
            application=self.app,
            skill_name="Stable",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("3.00"),
        )
        self._login()
        before = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        after = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        self.assertEqual(before, after)

    def test_get_portfolio_evidence_mapping_items_returns_only_unresolved_ordered(self):
        self._create_gap(
            application=self.app,
            skill_name="A",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="B",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="C",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
            resolved=True,
        )
        items = get_portfolio_evidence_mapping_items(user=self.user)
        self.assertEqual([gap.skill_name for gap in items], ["B", "A"])

    def test_portfolio_evidence_mapping_avoids_forbidden_claim_language(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("manual portfolio evidence mapping", content)
        self.assertIn("advisory only", content)
        self.assertIn("based on saved skill-gap records", content)
        self.assertIn("prompts only", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("auto-send", content)
        self.assertNotIn("predictive ai", content)
        self.assertNotIn("gmail", content)
        self.assertNotIn("oauth", content)
        self.assertNotIn("sprint 50", content)

    def test_no_model_changes_or_migrations_added(self):
        migration_dir = REPO_ROOT / "apps" / "skill_gaps" / "migrations"
        migration_files = [
            path.name
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]
        self.assertEqual(migration_files, ["0001_initial.py"])

    def test_sprint_48_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "apps" / "skill_gaps" / "services.py",
            REPO_ROOT / "apps" / "skill_gaps" / "views.py",
            REPO_ROOT / "apps" / "skill_gaps" / "tests.py",
            REPO_ROOT / "templates" / "skill_gaps" / "dashboard.html",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )


class SkillGapInterviewStoryMappingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="storyuser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="storyother",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:dashboard")
        self.app = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.other_app = JobApplication.objects.create(
            user=self.other_user,
            company_name="Rival",
            job_title="Engineer",
            date_applied=date(2026, 5, 11),
        )

    def _login(self):
        self.client.login(username="storyuser", password="StrongPass12345")

    def _create_gap(
        self,
        *,
        application,
        skill_name,
        priority,
        priority_score,
        resolved=False,
    ):
        return ApplicationSkillGap.objects.create(
            application=application,
            stage=SkillGapStage.APPLICATION,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=priority_score,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            suggested_action=f"Outline {skill_name} interview story manually.",
            resolved=resolved,
        )

    def test_interview_story_mapping_section_appears_on_dashboard(self):
        self._create_gap(
            application=self.app,
            skill_name="Python",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("8.00"),
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Manual interview story mapping")
        self.assertContains(response, "Interview story focus")
        self.assertContains(response, "Suggested story prompts")
        self.assertContains(response, "Situation prompt (manual)")
        self.assertContains(response, "Task prompt (manual)")
        self.assertContains(response, "Action prompt (manual)")
        self.assertContains(response, "Result prompt (manual)")
        self.assertContains(response, "Business impact prompt (manual)")
        self.assertContains(response, "Dashboard/reporting explanation prompt")
        self.assertContains(response, "Review and decide manually")

    def test_interview_story_mapping_context_is_user_scoped(self):
        self._create_gap(
            application=self.app,
            skill_name="SQL",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
        )
        self._create_gap(
            application=self.other_app,
            skill_name="HiddenSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        mapping = build_skill_gap_interview_story_mapping_context(user=self.user)
        names = {
            gap.skill_name
            for group in (
                mapping.prepare_interview_stories_now,
                mapping.strengthen_evidence_stories_next,
                mapping.story_backlog,
            )
            for gap in group.items
        }
        self.assertIn("SQL", names)
        self.assertNotIn("HiddenSkill", names)

    def test_high_priority_unresolved_appear_before_story_backlog(self):
        self._create_gap(
            application=self.app,
            skill_name="LowSkill",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="CriticalSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        mapping = build_skill_gap_interview_story_mapping_context(user=self.user)
        self.assertEqual(
            mapping.prepare_interview_stories_now.items[0].skill_name,
            "CriticalSkill",
        )
        self.assertEqual(mapping.story_backlog.items[0].skill_name, "LowSkill")

    def test_resolved_gaps_not_in_primary_interview_story_focus(self):
        self._create_gap(
            application=self.app,
            skill_name="OpenGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("7.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="DoneGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
            resolved=True,
        )
        mapping = build_skill_gap_interview_story_mapping_context(user=self.user)
        primary_names = [
            gap.skill_name for gap in mapping.prepare_interview_stories_now.items
        ]
        primary_names += [
            gap.skill_name for gap in mapping.strengthen_evidence_stories_next.items
        ]
        primary_names += [gap.skill_name for gap in mapping.story_backlog.items]
        self.assertEqual(primary_names, ["OpenGap"])
        self.assertEqual(mapping.resolved_story_context.items[0].skill_name, "DoneGap")

    def test_empty_interview_story_mapping_when_no_unresolved_gaps(self):
        self._create_gap(
            application=self.app,
            skill_name="DoneOnly",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
            resolved=True,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(
            response,
            "No unresolved skill gaps for manual interview story mapping",
        )
        mapping = build_skill_gap_interview_story_mapping_context(user=self.user)
        self.assertFalse(mapping.has_unresolved)

    def test_dashboard_get_does_not_mutate_skill_gaps_for_interview_story_mapping(self):
        self._create_gap(
            application=self.app,
            skill_name="Stable",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("3.00"),
        )
        self._login()
        before = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        after = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        self.assertEqual(before, after)

    def test_get_interview_story_mapping_items_returns_only_unresolved_ordered(self):
        self._create_gap(
            application=self.app,
            skill_name="A",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="B",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="C",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
            resolved=True,
        )
        items = get_interview_story_mapping_items(user=self.user)
        self.assertEqual([gap.skill_name for gap in items], ["B", "A"])

    def test_interview_story_mapping_avoids_forbidden_claim_language(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("manual interview story mapping", content)
        self.assertIn("advisory only", content)
        self.assertIn("based on saved skill-gap records", content)
        self.assertIn("manual prompts only", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("auto-send", content)
        self.assertNotIn("predictive ai", content)
        self.assertNotIn("gmail", content)
        self.assertNotIn("oauth", content)
        self.assertNotIn("sprint 51", content)

    def test_no_model_changes_or_migrations_added(self):
        migration_dir = REPO_ROOT / "apps" / "skill_gaps" / "migrations"
        migration_files = [
            path.name
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]
        self.assertEqual(migration_files, ["0001_initial.py"])

    def test_sprint_49_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "apps" / "skill_gaps" / "services.py",
            REPO_ROOT / "apps" / "skill_gaps" / "views.py",
            REPO_ROOT / "apps" / "skill_gaps" / "tests.py",
            REPO_ROOT / "templates" / "skill_gaps" / "dashboard.html",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )


class SkillGapCvBulletMappingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="cvuser", password="StrongPass12345")
        self.other_user = User.objects.create_user(
            username="cvother",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:dashboard")
        self.app = JobApplication.objects.create(
            user=self.user,
            company_name="Acme",
            job_title="Data Analyst",
            date_applied=date(2026, 5, 10),
        )
        self.other_app = JobApplication.objects.create(
            user=self.other_user,
            company_name="Rival",
            job_title="Engineer",
            date_applied=date(2026, 5, 11),
        )

    def _login(self):
        self.client.login(username="cvuser", password="StrongPass12345")

    def _create_gap(
        self,
        *,
        application,
        skill_name,
        priority,
        priority_score,
        resolved=False,
    ):
        return ApplicationSkillGap.objects.create(
            application=application,
            stage=SkillGapStage.APPLICATION,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=0,
            stage_weight=Decimal("1.00"),
            priority_score=priority_score,
            identified_by=SkillGapIdentifiedBy.MANUAL,
            suggested_action=f"Outline {skill_name} CV bullet ideas manually.",
            resolved=resolved,
        )

    def test_cv_bullet_mapping_section_appears_on_dashboard(self):
        self._create_gap(
            application=self.app,
            skill_name="Python",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("8.00"),
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Manual CV bullet mapping")
        self.assertContains(response, "CV bullet focus")
        self.assertContains(response, "Suggested CV bullet prompts")
        self.assertContains(response, "Skill evidence prompt (manual)")
        self.assertContains(response, "Project evidence prompt (manual)")
        self.assertContains(response, "Business impact prompt (manual)")
        self.assertContains(response, "Dashboard/reporting prompt")
        self.assertContains(response, "Keyword alignment prompt (manual)")
        self.assertContains(response, "Review and decide manually")

    def test_cv_bullet_mapping_context_is_user_scoped(self):
        self._create_gap(
            application=self.app,
            skill_name="SQL",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
        )
        self._create_gap(
            application=self.other_app,
            skill_name="HiddenSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        mapping = build_skill_gap_cv_bullet_mapping_context(user=self.user)
        names = {
            gap.skill_name
            for group in (
                mapping.draft_cv_bullet_prompts_now,
                mapping.strengthen_cv_evidence_next,
                mapping.cv_bullet_backlog,
            )
            for gap in group.items
        }
        self.assertIn("SQL", names)
        self.assertNotIn("HiddenSkill", names)

    def test_high_priority_unresolved_appear_before_cv_bullet_backlog(self):
        self._create_gap(
            application=self.app,
            skill_name="LowSkill",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="CriticalSkill",
            priority=SkillGapPriority.CRITICAL,
            priority_score=Decimal("12.00"),
        )
        mapping = build_skill_gap_cv_bullet_mapping_context(user=self.user)
        self.assertEqual(
            mapping.draft_cv_bullet_prompts_now.items[0].skill_name,
            "CriticalSkill",
        )
        self.assertEqual(mapping.cv_bullet_backlog.items[0].skill_name, "LowSkill")

    def test_resolved_gaps_not_in_primary_cv_bullet_focus(self):
        self._create_gap(
            application=self.app,
            skill_name="OpenGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("7.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="DoneGap",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
            resolved=True,
        )
        mapping = build_skill_gap_cv_bullet_mapping_context(user=self.user)
        primary_names = [
            gap.skill_name for gap in mapping.draft_cv_bullet_prompts_now.items
        ]
        primary_names += [gap.skill_name for gap in mapping.strengthen_cv_evidence_next.items]
        primary_names += [gap.skill_name for gap in mapping.cv_bullet_backlog.items]
        self.assertEqual(primary_names, ["OpenGap"])
        self.assertEqual(mapping.resolved_cv_context.items[0].skill_name, "DoneGap")

    def test_empty_cv_bullet_mapping_when_no_unresolved_gaps(self):
        self._create_gap(
            application=self.app,
            skill_name="DoneOnly",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
            resolved=True,
        )
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "No unresolved skill gaps for manual CV bullet mapping")
        mapping = build_skill_gap_cv_bullet_mapping_context(user=self.user)
        self.assertFalse(mapping.has_unresolved)

    def test_dashboard_get_does_not_mutate_skill_gaps_for_cv_bullet_mapping(self):
        self._create_gap(
            application=self.app,
            skill_name="Stable",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("3.00"),
        )
        self._login()
        before = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        after = ApplicationSkillGap.objects.filter(application__user=self.user).count()
        self.assertEqual(before, after)

    def test_get_cv_bullet_mapping_items_returns_only_unresolved_ordered(self):
        self._create_gap(
            application=self.app,
            skill_name="A",
            priority=SkillGapPriority.LOW,
            priority_score=Decimal("1.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="B",
            priority=SkillGapPriority.HIGH,
            priority_score=Decimal("9.00"),
        )
        self._create_gap(
            application=self.app,
            skill_name="C",
            priority=SkillGapPriority.MEDIUM,
            priority_score=Decimal("4.00"),
            resolved=True,
        )
        items = get_cv_bullet_mapping_items(user=self.user)
        self.assertEqual([gap.skill_name for gap in items], ["B", "A"])

    def test_cv_bullet_mapping_avoids_forbidden_claim_language(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("manual cv bullet mapping", content)
        self.assertIn("advisory only", content)
        self.assertIn("based on saved skill-gap records", content)
        self.assertIn("manual prompts only", content)
        self.assertIn("does not rewrite your cv automatically", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("auto-send", content)
        self.assertNotIn("predictive ai", content)
        self.assertNotIn("automatic cv rewriting", content)
        self.assertNotIn("gmail", content)
        self.assertNotIn("oauth", content)
        self.assertNotIn("sprint 52", content)

    def test_no_model_changes_or_migrations_added(self):
        migration_dir = REPO_ROOT / "apps" / "skill_gaps" / "migrations"
        migration_files = [
            path.name
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]
        self.assertEqual(migration_files, ["0001_initial.py"])

    def test_sprint_50_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "apps" / "skill_gaps" / "services.py",
            REPO_ROOT / "apps" / "skill_gaps" / "views.py",
            REPO_ROOT / "apps" / "skill_gaps" / "tests.py",
            REPO_ROOT / "templates" / "skill_gaps" / "dashboard.html",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )


class SkillGapSprint51ReviewerWalkthroughTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="revuser", password="StrongPass12345")
        self.url = reverse("skill_gaps:dashboard")

    def _login(self):
        self.client.login(username="revuser", password="StrongPass12345")

    def test_skill_gaps_dashboard_renders_reviewer_workflow_copy(self):
        self._login()
        response = self.client.get(self.url)
        self.assertContains(response, "Reviewer walkthrough")
        self.assertContains(response, "Skill gaps workflow (manual and advisory)")
        self.assertContains(response, "Manual action plan")
        self.assertContains(response, "Manual CV bullet mapping")
        self.assertContains(response, "Review and decide manually")

    def test_sprint_51_reviewer_copy_remains_claim_safe(self):
        self._login()
        response = self.client.get(self.url)
        content = response.content.decode().lower()
        self.assertIn("advisory only", content)
        self.assertIn("based on saved skill-gap records", content)
        self.assertIn("not implemented on this page", content)
        self.assertIn("external account integrations", content)
        self.assertIn("finished cv edits", content)
        self.assertNotIn("sprint 52", content)

    def test_sprint_51_changed_files_are_ascii_safe(self):
        ascii_paths = (
            REPO_ROOT / "templates" / "skill_gaps" / "dashboard.html",
            REPO_ROOT / "docs" / "evidence" / "sprint_51_final_reviewer_walkthrough_polish.md",
        )
        for path in ascii_paths:
            content = path.read_text(encoding="utf-8")
            self.assertTrue(
                all(ord(char) < 128 for char in content),
                msg=f"Non-ASCII character found in {path}",
            )


class SkillGapAiCareerCoachArchitectureTests(TestCase):
    def _matched_rows(self):
        return (
            {
                "term": "Python",
                "ledger_status": SkillEntry.EvidenceLevel.VERIFIED,
                "display_label": "VERIFIED",
                "matched_skill_name": "Python",
                "is_in_ledger": True,
            },
            {
                "term": "Snowflake",
                "ledger_status": SkillEntry.EvidenceLevel.LEARNING_TARGET,
                "display_label": "LEARNING_TARGET",
                "matched_skill_name": "Snowflake",
                "is_in_ledger": True,
            },
            {
                "term": "Statistics",
                "ledger_status": SkillEntry.EvidenceLevel.STUDYING,
                "display_label": "STUDYING",
                "matched_skill_name": "Statistics",
                "is_in_ledger": True,
            },
            {
                "term": "GraphQL",
                "ledger_status": SkillEntry.EvidenceLevel.NO_EVIDENCE,
                "display_label": "NO_EVIDENCE",
                "matched_skill_name": "GraphQL",
                "is_in_ledger": True,
            },
            {
                "term": "Airflow",
                "ledger_status": "NOT_IN_LEDGER",
                "display_label": "Not in Skill Ledger",
                "matched_skill_name": "",
                "is_in_ledger": False,
            },
        )

    def _payload(self):
        return build_evidence_payload(
            matched_gap_rows=self._matched_rows(),
            project_evidence=(
                {
                    "evidence_reference": "project:portfolio-dashboard",
                    "title": "Portfolio dashboard",
                    "evidence_type": "project",
                    "summary": "Dashboard evidence for Python analytics work.",
                    "company_name": "Hidden Employer",
                    "private_notes": "Do not expose this note.",
                    "email": "private@example.com",
                },
            ),
        )

    def _safe_response(self):
        return {
            "evidence_backed_strengths": [
                {
                    "skill": "Python",
                    "summary": "Python can be discussed as portfolio-evidenced.",
                    "evidence_reference": "VERIFIED:python",
                },
            ],
            "skills_needing_evidence": [
                {
                    "skill": "GraphQL",
                    "summary": "GraphQL needs more supplied evidence before claiming.",
                    "evidence_reference": "NO_EVIDENCE:graphql",
                },
                {
                    "skill": "Airflow",
                    "summary": "Airflow is not in the supplied Skill Ledger rows.",
                    "evidence_reference": "NOT_IN_LEDGER:airflow",
                },
            ],
            "learning_targets": [
                {
                    "skill": "Snowflake",
                    "summary": "Snowflake should stay framed as a learning target.",
                    "evidence_reference": "LEARNING_TARGET:snowflake",
                },
            ],
            "claim_safety_warnings": [
                {
                    "skill": "GraphQL",
                    "summary": "Do not present GraphQL as supported by supplied proof.",
                },
            ],
            "recommended_next_actions": [
                {
                    "skill": "Statistics",
                    "summary": "Review study notes and add project evidence manually.",
                    "evidence_reference": "STUDYING:statistics",
                },
            ],
            "manual_review_required": True,
        }

    def test_ai_career_coach_builds_expected_evidence_payload_keys(self):
        payload = self._payload()

        self.assertEqual(tuple(payload.keys()), EVIDENCE_PAYLOAD_KEYS)

    def test_ai_career_coach_payload_separates_evidence_levels(self):
        payload = self._payload()

        self.assertEqual(payload["verified_skills"][0]["skill_name"], "Python")
        self.assertEqual(payload["learning_target_skills"][0]["skill_name"], "Snowflake")
        self.assertEqual(payload["studying_skills"][0]["skill_name"], "Statistics")
        self.assertEqual(payload["no_evidence_skills"][0]["skill_name"], "GraphQL")

    def test_ai_career_coach_payload_tracks_not_in_ledger_terms(self):
        payload = self._payload()

        self.assertEqual(payload["not_in_ledger_terms"], ["Airflow"])
        self.assertEqual(payload["no_evidence_skills"][0]["skill_name"], "GraphQL")

    def test_ai_career_coach_prompt_includes_required_safety_rules(self):
        prompt = build_controlled_prompt(self._payload())

        for rule in REQUIRED_PROMPT_SAFETY_RULES:
            with self.subTest(rule=rule):
                self.assertIn(rule, prompt)
        self.assertIn("Return JSON only.", prompt)
        self.assertNotIn("Hidden Employer", prompt)
        self.assertNotIn("private@example.com", prompt)
        self.assertNotIn("Do not expose this note.", prompt)

    def test_ai_career_coach_prompt_is_deterministic(self):
        payload = self._payload()

        self.assertEqual(build_controlled_prompt(payload), build_controlled_prompt(payload))

    def test_ai_career_coach_expected_response_schema_requires_manual_review(self):
        schema = expected_response_schema()

        self.assertTrue(schema["manual_review_required"])
        for key in (
            "evidence_backed_strengths",
            "skills_needing_evidence",
            "learning_targets",
            "claim_safety_warnings",
            "recommended_next_actions",
        ):
            with self.subTest(key=key):
                self.assertEqual(schema[key], [])

    def test_ai_career_coach_validator_accepts_safe_evidence_referenced_response(self):
        result = validate_career_coach_response(
            json.dumps(self._safe_response()),
            evidence_payload=self._payload(),
        )

        self.assertTrue(result.is_valid)
        self.assertEqual(result.errors, ())
        self.assertEqual(result.safe_response, self._safe_response())

    def test_ai_career_coach_validator_rejects_non_json_response(self):
        result = validate_career_coach_response(
            "Here is career guidance.",
            evidence_payload=self._payload(),
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, ("non_json_response",))

    def test_ai_career_coach_validator_rejects_empty_response(self):
        result = validate_career_coach_response("", evidence_payload=self._payload())

        self.assertFalse(result.is_valid)
        self.assertEqual(result.errors, ("empty_response",))

    def test_ai_career_coach_validator_rejects_unsafe_response_shape(self):
        response = self._safe_response()
        response.pop("manual_review_required")

        result = validate_career_coach_response(response, evidence_payload=self._payload())

        self.assertFalse(result.is_valid)
        self.assertIn("unsafe_response_shape", result.errors)

    def test_ai_career_coach_validator_rejects_manual_review_false(self):
        response = self._safe_response()
        response["manual_review_required"] = False

        result = validate_career_coach_response(response, evidence_payload=self._payload())

        self.assertFalse(result.is_valid)
        self.assertIn("manual_review_required_false", result.errors)

    def test_ai_career_coach_validator_rejects_unsupported_skill(self):
        response = self._safe_response()
        response["recommended_next_actions"][0]["skill"] = "Kubernetes"

        result = validate_career_coach_response(response, evidence_payload=self._payload())

        self.assertFalse(result.is_valid)
        self.assertIn("unsupported_skill", result.errors)

    def test_ai_career_coach_validator_rejects_learning_target_as_current_proficiency(
        self,
    ):
        response = self._safe_response()
        response["learning_targets"][0][
            "summary"
        ] = "Snowflake is current proficiency for the user."

        result = validate_career_coach_response(response, evidence_payload=self._payload())

        self.assertFalse(result.is_valid)
        self.assertIn("learning_target_current_proficiency_overclaim", result.errors)

    def test_ai_career_coach_validator_rejects_no_evidence_as_evidence_backed(self):
        response = self._safe_response()
        response["skills_needing_evidence"][0][
            "summary"
        ] = "GraphQL is evidence-backed and ready to claim."

        result = validate_career_coach_response(response, evidence_payload=self._payload())

        self.assertFalse(result.is_valid)
        self.assertIn("no_evidence_backed_overclaim", result.errors)

    def test_ai_career_coach_validator_rejects_missing_evidence_reference(self):
        response = self._safe_response()
        response["recommended_next_actions"][0]["evidence_reference"] = ""

        result = validate_career_coach_response(response, evidence_payload=self._payload())

        self.assertFalse(result.is_valid)
        self.assertIn("missing_evidence_reference", result.errors)

    def test_ai_career_coach_module_has_no_live_provider_or_external_call_terms(self):
        module_source = (
            REPO_ROOT / "apps" / "skill_gaps" / "ai_career_coach.py"
        ).read_text(encoding="utf-8")
        forbidden_terms = (
            "openai",
            "anthropic",
            "gemini",
            "requests",
            "httpx",
            "aiohttp",
            "api_key",
            "os.environ",
            "streaming",
            "timeout",
            "retry",
        )

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, module_source.lower())


class SkillGapMockedAiCareerCoachPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="coachuser",
            password="StrongPass12345",
        )
        self.url = reverse("skill_gaps:ai_career_coach")
        self.application = JobApplication.objects.create(
            user=self.user,
            company_name="Hidden Employer",
            job_title="Private Role",
            date_applied=date(2026, 6, 1),
            required_skills="Python Snowflake GraphQL",
        )

    def _login(self):
        self.client.login(username="coachuser", password="StrongPass12345")

    def _create_gap(self, skill_name, priority=SkillGapPriority.MEDIUM):
        return ApplicationSkillGap.objects.create(
            application=self.application,
            stage=SkillGapStage.APPLICATION,
            skill_name=skill_name,
            current_tier=SkillTier.MISSING,
            priority=priority,
            goal_weight=Decimal("1.00"),
            failure_count=1,
            stage_weight=Decimal("1.00"),
            priority_score=Decimal("4.00"),
            identified_by=SkillGapIdentifiedBy.MANUAL,
            suggested_action=f"Review {skill_name} manually.",
        )

    def _create_skill_entry(self, skill_name, evidence_level):
        return SkillEntry.objects.create(
            skill_name=skill_name,
            category=SkillEntry.Category.PROGRAMMING,
            evidence_level=evidence_level,
            sprint_reference="Sprint 81",
            project_link="https://example.com/private-evidence",
            notes="Private note must not render.",
            visibility=SkillEntry.Visibility.PRIVATE,
        )

    def _seed_evidence(self):
        self._create_gap("Python", priority=SkillGapPriority.HIGH)
        self._create_gap("Snowflake")
        self._create_gap("GraphQL")
        self._create_skill_entry("Python", SkillEntry.EvidenceLevel.VERIFIED)
        self._create_skill_entry("Snowflake", SkillEntry.EvidenceLevel.LEARNING_TARGET)
        self._create_skill_entry("GraphQL", SkillEntry.EvidenceLevel.NO_EVIDENCE)

    def _payload(self):
        return build_evidence_payload(
            matched_gap_rows=(
                {
                    "term": "Python",
                    "ledger_status": SkillEntry.EvidenceLevel.VERIFIED,
                    "display_label": "VERIFIED",
                    "matched_skill_name": "Python",
                    "is_in_ledger": True,
                },
                {
                    "term": "Snowflake",
                    "ledger_status": SkillEntry.EvidenceLevel.LEARNING_TARGET,
                    "display_label": "LEARNING_TARGET",
                    "matched_skill_name": "Snowflake",
                    "is_in_ledger": True,
                },
                {
                    "term": "GraphQL",
                    "ledger_status": SkillEntry.EvidenceLevel.NO_EVIDENCE,
                    "display_label": "NO_EVIDENCE",
                    "matched_skill_name": "GraphQL",
                    "is_in_ledger": True,
                },
            ),
        )

    def test_ai_career_coach_page_loads_for_authenticated_user(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Evidence-grounded career review")
        self.assertContains(response, "Skill and gap planning output")

    def test_ai_career_coach_page_redirects_anonymous_user(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response["Location"])

    def test_ai_career_coach_page_is_get_only(self):
        self._login()

        response = self.client.post(self.url, {"prompt": "save"})

        self.assertEqual(response.status_code, 405)

    def test_ai_career_coach_view_calls_evidence_payload_builder(self):
        self._seed_evidence()
        self._login()

        with patch(
            "apps.skill_gaps.views.ai_career_coach.build_evidence_payload",
            wraps=build_evidence_payload,
        ) as mocked_builder:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked_builder.called)

    def test_ai_career_coach_view_calls_prompt_builder(self):
        self._seed_evidence()
        self._login()

        with patch(
            "apps.skill_gaps.views.ai_career_coach.build_controlled_prompt",
            wraps=build_controlled_prompt,
        ) as mocked_prompt_builder:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked_prompt_builder.called)

    def test_ai_career_coach_view_passes_response_through_validator(self):
        self._seed_evidence()
        self._login()

        with patch(
            "apps.skill_gaps.views.ai_career_coach.validate_career_coach_response",
            wraps=validate_career_coach_response,
        ) as mocked_validator:
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked_validator.called)

    def test_ai_career_coach_mocked_response_passes_validator(self):
        payload = self._payload()
        mocked_response = build_mocked_career_coach_response(payload)

        result = validate_career_coach_response(
            mocked_response,
            evidence_payload=payload,
        )

        self.assertTrue(result.is_valid)
        self.assertTrue(result.safe_response["manual_review_required"])

    def test_ai_career_coach_view_renders_validated_output_only(self):
        self._seed_evidence()
        self._login()
        unsafe_response = build_mocked_career_coach_response(self._payload())
        unsafe_response["recommended_next_actions"][0]["skill"] = "UNSAFE_SENTINEL"
        unsafe_response["recommended_next_actions"][0][
            "summary"
        ] = "UNSAFE_SENTINEL should not render."

        with patch(
            "apps.skill_gaps.views.ai_career_coach.build_mocked_career_coach_response",
            return_value=unsafe_response,
        ):
            response = self.client.get(self.url)

        self.assertContains(response, "Career planning summary unavailable")
        self.assertNotContains(response, "UNSAFE_SENTINEL")

    def test_ai_career_coach_advisory_panel_present(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(
            response,
            (
                "This is a private planning tool. Output is generated from your manually "
                "maintained Skill Ledger and saved job description signals only. It does "
                "not assess employer requirements, verify proficiency, predict job "
                "outcomes, or guarantee employability. All output is advisory. Use your "
                "own judgement."
            ),
        )
        self.assertContains(
            response,
            (
                "This output was generated from structured career data using a "
                "controlled workflow. It does not constitute professional career advice."
            ),
        )

    def test_ai_career_coach_does_not_imply_employer_requirement_met(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        for phrase in (
            "Employer confirmed",
            "Skill verified",
            "You are ready for this role",
            "You meet the requirements",
            "employer requirement is met",
        ):
            with self.subTest(phrase=phrase):
                self.assertNotIn(phrase, content)

    def test_ai_career_coach_does_not_imply_live_ai_generating_output(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode()

        self.assertContains(
            response,
            (
                "Output is generated from a controlled example workflow. "
                "No live AI model is used in this version."
            ),
        )
        self.assertNotIn("AI recommends", content)
        self.assertNotIn("Automatically generated by AI", content)

    def test_ai_career_coach_read_only_wording_present(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "No output is saved.")
        self.assertContains(response, "No application is submitted.")
        self.assertContains(response, "No CV/profile is updated.")

    def test_ai_career_coach_manual_review_wording_present(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)

        self.assertContains(response, "Manual review is required.")
        self.assertContains(response, "Manual review is required before using any wording")

    def test_ai_career_coach_no_auto_apply_or_submission_implied(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)
        content = response.content.decode().lower()

        self.assertIn("no application is submitted", content)
        self.assertNotIn("auto-apply", content)
        self.assertNotIn("submitted to employer", content)
        self.assertNotIn("gmail", content)
        self.assertNotIn("oauth", content)

    def test_ai_career_coach_does_not_make_external_api_call(self):
        source = (
            REPO_ROOT / "apps" / "skill_gaps" / "ai_career_coach.py"
        ).read_text(encoding="utf-8")
        view_source = (REPO_ROOT / "apps" / "skill_gaps" / "views.py").read_text(
            encoding="utf-8",
        )
        forbidden_terms = ("openai", "anthropic", "gemini", "httpx", "aiohttp")

        for term in forbidden_terms:
            with self.subTest(term=term):
                self.assertNotIn(term, source.lower())
                self.assertNotIn(term, view_source.lower())

    def test_ai_career_coach_uses_mocked_provider_only(self):
        source = (
            REPO_ROOT / "apps" / "skill_gaps" / "ai_career_coach.py"
        ).read_text(encoding="utf-8")

        self.assertIn("build_mocked_career_coach_response", source)
        self.assertNotIn("ai_providers", source)
        self.assertNotIn("provider abstraction", source.lower())

    def test_ai_career_coach_validator_would_reject_unsafe_claim(self):
        payload = self._payload()
        response = build_mocked_career_coach_response(payload)
        response["recommended_next_actions"][0][
            "summary"
        ] = "This meets employer requirement and predicts a hiring outcome."

        result = validate_career_coach_response(response, evidence_payload=payload)

        self.assertFalse(result.is_valid)
        self.assertIn("forbidden_outcome_prediction", result.errors)

    def test_ai_career_coach_handles_empty_skill_ledger_gracefully(self):
        self._create_gap("Airflow")
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your Skill Ledger has no entries available")
        self.assertContains(response, "Skill and gap planning output")

    def test_ai_career_coach_handles_no_jd_ready_records_gracefully(self):
        self._login()

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No JD-ready Skill Ledger match rows are available")
        self.assertContains(response, "No supplied Skill Ledger or gap rows were available")

    def test_ai_career_coach_does_not_render_private_record_details(self):
        self._seed_evidence()
        self._login()

        response = self.client.get(self.url)

        self.assertNotContains(response, "Hidden Employer")
        self.assertNotContains(response, "Private Role")
        self.assertNotContains(response, "Private note must not render.")

    def test_ai_career_coach_no_model_or_migration_change_required(self):
        migration_dir = REPO_ROOT / "apps" / "skill_gaps" / "migrations"
        migration_files = [
            path.name
            for path in migration_dir.glob("*.py")
            if path.name != "__init__.py"
        ]

        self.assertEqual(migration_files, ["0001_initial.py"])
