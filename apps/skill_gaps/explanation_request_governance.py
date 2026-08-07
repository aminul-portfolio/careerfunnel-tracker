"""Per-user daily request-count governance for advisory explanations.

Isolated from provider composition and JD Gap Analysis route integration.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.db import DatabaseError, IntegrityError
from django.db.models import F
from django.utils import timezone

from apps.skill_gaps.models import ExplanationRequestCounter

REASON_COUNT_LIMIT_REACHED = "COUNT_LIMIT_REACHED"
REASON_GOVERNANCE_CONFIGURATION_INVALID = "GOVERNANCE_CONFIGURATION_INVALID"
REASON_GOVERNANCE_STORAGE_UNAVAILABLE = "GOVERNANCE_STORAGE_UNAVAILABLE"


@dataclass(frozen=True)
class ExplanationRequestReservationDecision:
    allowed: bool
    reason_code: str | None


def _validated_daily_limit() -> int | None:
    """Return a strict positive int limit, else None for fail-closed."""

    raw = getattr(
        settings,
        "AI_EVIDENCE_ALIGNMENT_EXPLANATION_DAILY_REQUEST_LIMIT",
        None,
    )
    # bool is a subclass of int; exact type int is required.
    if type(raw) is not int or raw <= 0:
        return None
    return raw


def reserve_explanation_request(user) -> ExplanationRequestReservationDecision:
    """Reserve one daily explanation request for the authenticated user.

    Performs no provider access and accepts no requirement/prompt/output text.
    """

    daily_limit = _validated_daily_limit()
    if daily_limit is None:
        return ExplanationRequestReservationDecision(
            allowed=False,
            reason_code=REASON_GOVERNANCE_CONFIGURATION_INVALID,
        )

    current_date = timezone.localdate()
    try:
        counter, created = ExplanationRequestCounter.objects.get_or_create(
            user=user,
            window_date=current_date,
            defaults={"request_count": 1},
        )
        if created:
            return ExplanationRequestReservationDecision(
                allowed=True,
                reason_code=None,
            )

        updated = ExplanationRequestCounter.objects.filter(
            pk=counter.pk,
            request_count__lt=daily_limit,
        ).update(
            request_count=F("request_count") + 1,
        )
        if updated == 1:
            return ExplanationRequestReservationDecision(
                allowed=True,
                reason_code=None,
            )
        return ExplanationRequestReservationDecision(
            allowed=False,
            reason_code=REASON_COUNT_LIMIT_REACHED,
        )
    except (DatabaseError, IntegrityError):
        return ExplanationRequestReservationDecision(
            allowed=False,
            reason_code=REASON_GOVERNANCE_STORAGE_UNAVAILABLE,
        )
