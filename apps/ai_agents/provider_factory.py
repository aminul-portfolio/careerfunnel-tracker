"""Shared live-provider composition gate.

Provider mode is authoritative. An API key is necessary but never sufficient.
This module is the only place that reads or interprets AI_EXPLANATION_PROVIDER
and decides whether existing Claude factories may be constructed.
"""

from __future__ import annotations

from django.conf import settings

from .claude_provider import (
    ClaudeTelemetryProvider,
    make_claude_cv_tailoring_provider,
    make_claude_cv_tailoring_telemetry_provider,
    make_claude_evidence_alignment_explanation_provider,
    make_claude_fit_telemetry_provider,
    make_claude_provider,
)
from .provider_contracts import ExplanationProvider

LIVE_PROVIDER_MODE = "live"
MOCK_PROVIDER_MODE = "mock"


def _normalise_provider_mode(raw_mode: object) -> str:
    if raw_mode is None:
        return MOCK_PROVIDER_MODE
    if not isinstance(raw_mode, str):
        return MOCK_PROVIDER_MODE
    normalised = raw_mode.strip().lower()
    if not normalised:
        return MOCK_PROVIDER_MODE
    return normalised


def _api_key() -> str:
    raw = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not isinstance(raw, str):
        return ""
    return raw.strip()


def live_providers_permitted() -> bool:
    """True only when mode normalises to live and a non-empty API key is present."""
    mode = _normalise_provider_mode(
        getattr(settings, "AI_EXPLANATION_PROVIDER", MOCK_PROVIDER_MODE)
    )
    if mode != LIVE_PROVIDER_MODE:
        return False
    return bool(_api_key())


def compose_fit_scoring_provider() -> ExplanationProvider | None:
    """Return the fit-scoring provider callable, or None when live is not permitted."""
    if not live_providers_permitted():
        return None
    return make_claude_provider(_api_key())


def compose_cv_tailoring_provider() -> ExplanationProvider | None:
    """Return the CV-tailoring provider callable, or None when live is not permitted."""
    if not live_providers_permitted():
        return None
    return make_claude_cv_tailoring_provider(_api_key())


def compose_fit_scoring_telemetry_provider() -> ClaudeTelemetryProvider | None:
    """Return the fit-scoring telemetry provider, or None when live is not permitted."""
    if not live_providers_permitted():
        return None
    return make_claude_fit_telemetry_provider(_api_key())


def compose_cv_tailoring_telemetry_provider() -> ClaudeTelemetryProvider | None:
    """Return the CV telemetry provider, or None when live is not permitted."""
    if not live_providers_permitted():
        return None
    return make_claude_cv_tailoring_telemetry_provider(_api_key())


def compose_evidence_alignment_explanation_provider() -> ExplanationProvider | None:
    """Return the evidence-alignment explanation provider, or None when gated off.

    Requires the dedicated feature flag and live_providers_permitted(). Does not
    add a separate key-presence Boolean gate; _api_key() is used only to obtain
    the already-permitted key for factory construction.
    """
    if not getattr(settings, "AI_EVIDENCE_ALIGNMENT_EXPLANATION_ENABLED", False):
        return None
    if not live_providers_permitted():
        return None
    return make_claude_evidence_alignment_explanation_provider(_api_key())
