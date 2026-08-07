"""Sprint 118 Phase 2A: explanation request-count governance foundation."""

from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import DatabaseError, IntegrityError, transaction
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

from apps.skill_gaps.explanation_request_governance import (
    REASON_COUNT_LIMIT_REACHED,
    REASON_GOVERNANCE_CONFIGURATION_INVALID,
    REASON_GOVERNANCE_STORAGE_UNAVAILABLE,
    ExplanationRequestReservationDecision,
    reserve_explanation_request,
)
from apps.skill_gaps.models import ExplanationRequestCounter

User = get_user_model()

APPROVED_FIELD_NAMES = frozenset(
    {
        "id",
        "user",
        "window_date",
        "request_count",
        "created_at",
        "updated_at",
    }
)
FORBIDDEN_FIELD_FRAGMENTS = (
    "requirement",
    "prompt",
    "payload",
    "explanation",
    "response",
    "exception",
    "token",
    "cost",
    "hash",
    "request_id",
    "model",
    "provider",
    "outcome",
    "telemetry",
)


class ExplanationRequestCounterModelTests(TestCase):
    def test_model_contains_only_approved_governance_fields_plus_pk(self):
        field_names = {field.name for field in ExplanationRequestCounter._meta.get_fields()}
        self.assertEqual(field_names, APPROVED_FIELD_NAMES)

    def test_sensitive_content_and_telemetry_fields_are_absent(self):
        field_names = {
            field.name.lower() for field in ExplanationRequestCounter._meta.get_fields()
        }
        for fragment in FORBIDDEN_FIELD_FRAGMENTS:
            matching = {name for name in field_names if fragment in name}
            # "user" and timestamps are approved; fragment checks target other names.
            matching.discard("user")
            matching.discard("user_id")
            self.assertEqual(matching, set(), msg=f"forbidden fragment={fragment}")


class ExplanationRequestCounterConstraintTests(TransactionTestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="s118p2a_a", password="pass")
        self.user_b = User.objects.create_user(username="s118p2a_b", password="pass")
        self.day = date(2026, 8, 7)

    def test_same_user_same_date_uniqueness_is_enforced(self):
        ExplanationRequestCounter.objects.create(
            user=self.user_a,
            window_date=self.day,
            request_count=1,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ExplanationRequestCounter.objects.create(
                    user=self.user_a,
                    window_date=self.day,
                    request_count=1,
                )

    def test_different_users_may_use_the_same_date(self):
        ExplanationRequestCounter.objects.create(
            user=self.user_a,
            window_date=self.day,
            request_count=1,
        )
        other = ExplanationRequestCounter.objects.create(
            user=self.user_b,
            window_date=self.day,
            request_count=1,
        )
        self.assertEqual(other.window_date, self.day)
        self.assertEqual(
            ExplanationRequestCounter.objects.filter(window_date=self.day).count(),
            2,
        )

    def test_same_user_may_use_different_dates(self):
        ExplanationRequestCounter.objects.create(
            user=self.user_a,
            window_date=self.day,
            request_count=1,
        )
        next_day = ExplanationRequestCounter.objects.create(
            user=self.user_a,
            window_date=self.day + timedelta(days=1),
            request_count=1,
        )
        self.assertEqual(
            ExplanationRequestCounter.objects.filter(user=self.user_a).count(),
            2,
        )
        self.assertEqual(next_day.window_date, self.day + timedelta(days=1))

    def test_request_count_zero_violates_db_check_constraint(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ExplanationRequestCounter.objects.create(
                    user=self.user_a,
                    window_date=self.day,
                    request_count=0,
                )


class ExplanationRequestGovernanceServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="s118p2a_owner", password="pass")
        self.other = User.objects.create_user(username="s118p2a_other", password="pass")

    def _assert_blocked(self, decision, reason_code):
        self.assertIsInstance(decision, ExplanationRequestReservationDecision)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason_code, reason_code)

    def _assert_allowed(self, decision):
        self.assertIsInstance(decision, ExplanationRequestReservationDecision)
        self.assertTrue(decision.allowed)
        self.assertIsNone(decision.reason_code)

    def test_missing_limit_fails_closed(self):
        class _SettingsWithoutLimit:
            pass

        with patch(
            "apps.skill_gaps.explanation_request_governance.settings",
            _SettingsWithoutLimit(),
        ):
            decision = reserve_explanation_request(self.user)
        self._assert_blocked(decision, REASON_GOVERNANCE_CONFIGURATION_INVALID)
        self.assertEqual(ExplanationRequestCounter.objects.count(), 0)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=0)
    def test_zero_limit_fails_closed(self):
        decision = reserve_explanation_request(self.user)
        self._assert_blocked(decision, REASON_GOVERNANCE_CONFIGURATION_INVALID)
        self.assertEqual(ExplanationRequestCounter.objects.count(), 0)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=-1)
    def test_negative_limit_fails_closed(self):
        decision = reserve_explanation_request(self.user)
        self._assert_blocked(decision, REASON_GOVERNANCE_CONFIGURATION_INVALID)
        self.assertEqual(ExplanationRequestCounter.objects.count(), 0)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=True)
    def test_boolean_limit_fails_closed(self):
        decision = reserve_explanation_request(self.user)
        self._assert_blocked(decision, REASON_GOVERNANCE_CONFIGURATION_INVALID)
        self.assertEqual(ExplanationRequestCounter.objects.count(), 0)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT="5")
    def test_string_limit_fails_closed(self):
        decision = reserve_explanation_request(self.user)
        self._assert_blocked(decision, REASON_GOVERNANCE_CONFIGURATION_INVALID)
        self.assertEqual(ExplanationRequestCounter.objects.count(), 0)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=5)
    def test_first_valid_reservation_creates_request_count_one(self):
        decision = reserve_explanation_request(self.user)
        self._assert_allowed(decision)
        counter = ExplanationRequestCounter.objects.get(user=self.user)
        self.assertEqual(counter.request_count, 1)
        self.assertEqual(counter.window_date, timezone.localdate())

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=5)
    def test_reservation_below_limit_increments_existing_row(self):
        first = reserve_explanation_request(self.user)
        second = reserve_explanation_request(self.user)
        self._assert_allowed(first)
        self._assert_allowed(second)
        counter = ExplanationRequestCounter.objects.get(user=self.user)
        self.assertEqual(counter.request_count, 2)
        self.assertEqual(ExplanationRequestCounter.objects.count(), 1)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=3)
    def test_reservation_reaching_exact_limit_is_allowed(self):
        for _ in range(3):
            self._assert_allowed(reserve_explanation_request(self.user))
        counter = ExplanationRequestCounter.objects.get(user=self.user)
        self.assertEqual(counter.request_count, 3)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=3)
    def test_next_reservation_beyond_limit_is_blocked(self):
        for _ in range(3):
            self._assert_allowed(reserve_explanation_request(self.user))
        blocked = reserve_explanation_request(self.user)
        self._assert_blocked(blocked, REASON_COUNT_LIMIT_REACHED)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=3)
    def test_blocked_reservation_does_not_increment(self):
        for _ in range(3):
            reserve_explanation_request(self.user)
        before = ExplanationRequestCounter.objects.get(user=self.user).request_count
        blocked = reserve_explanation_request(self.user)
        self._assert_blocked(blocked, REASON_COUNT_LIMIT_REACHED)
        after = ExplanationRequestCounter.objects.get(user=self.user).request_count
        self.assertEqual(after, before)
        self.assertEqual(after, 3)

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1)
    def test_limit_one_allows_first_and_blocks_second(self):
        first = reserve_explanation_request(self.user)
        second = reserve_explanation_request(self.user)
        self._assert_allowed(first)
        self._assert_blocked(second, REASON_COUNT_LIMIT_REACHED)
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=self.user).request_count,
            1,
        )

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1)
    def test_quotas_are_isolated_between_users(self):
        self._assert_allowed(reserve_explanation_request(self.user))
        self._assert_blocked(
            reserve_explanation_request(self.user),
            REASON_COUNT_LIMIT_REACHED,
        )
        self._assert_allowed(reserve_explanation_request(self.other))
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=self.user).request_count,
            1,
        )
        self.assertEqual(
            ExplanationRequestCounter.objects.get(user=self.other).request_count,
            1,
        )

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=1)
    def test_new_local_calendar_date_gets_separate_counter(self):
        day_one = date(2026, 8, 7)
        day_two = date(2026, 8, 8)
        with patch(
            "apps.skill_gaps.explanation_request_governance.timezone.localdate",
            return_value=day_one,
        ):
            self._assert_allowed(reserve_explanation_request(self.user))
            self._assert_blocked(
                reserve_explanation_request(self.user),
                REASON_COUNT_LIMIT_REACHED,
            )
        with patch(
            "apps.skill_gaps.explanation_request_governance.timezone.localdate",
            return_value=day_two,
        ):
            self._assert_allowed(reserve_explanation_request(self.user))
        self.assertEqual(
            ExplanationRequestCounter.objects.filter(user=self.user).count(),
            2,
        )
        self.assertEqual(
            ExplanationRequestCounter.objects.get(
                user=self.user,
                window_date=day_one,
            ).request_count,
            1,
        )
        self.assertEqual(
            ExplanationRequestCounter.objects.get(
                user=self.user,
                window_date=day_two,
            ).request_count,
            1,
        )

    @override_settings(AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT=5)
    def test_database_failure_returns_storage_unavailable_without_leak(self):
        with patch(
            "apps.skill_gaps.explanation_request_governance."
            "ExplanationRequestCounter.objects.get_or_create",
            side_effect=DatabaseError("secret-db-detail-s118"),
        ):
            decision = reserve_explanation_request(self.user)
        self._assert_blocked(decision, REASON_GOVERNANCE_STORAGE_UNAVAILABLE)
        self.assertEqual(ExplanationRequestCounter.objects.count(), 0)
        self.assertNotIn("secret-db-detail-s118", repr(decision))
        self.assertNotIn("DatabaseError", repr(decision))
