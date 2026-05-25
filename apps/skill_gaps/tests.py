from datetime import date
from decimal import Decimal
from pathlib import Path

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.urls import NoReverseMatch, reverse

from apps.applications.choices import ApplicationStatus
from apps.applications.models import JobApplication

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
    compute_priority_score,
    create_or_update_gap,
    get_global_failure_count,
    get_goal_weight,
    get_stage_weight,
    mark_gap_resolved,
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
    def test_no_dashboard_route_page_added(self):
        with self.assertRaises(NoReverseMatch):
            reverse("skill_gaps:dashboard")
        with self.assertRaises(NoReverseMatch):
            reverse("skill_gaps:skill_gap_list")

    def test_no_sprint_44_text_in_skill_gaps_app(self):
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
