from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any

from . import ai_career_coach
from .jd_requirement_enrichment import (
    REQUIRED_ENRICHMENT_SAFETY_WORDING,
    build_mocked_enrichment_candidates,
)

ANTHROPIC_MODEL = "claude-haiku-4-5"
ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
LIVE_PROVIDER_TIMEOUT_SECONDS = 10
MAX_PROVIDER_RESPONSE_TEXT_LENGTH = 20000
JD_ENRICHMENT_ALLOWED_PAYLOAD_KEYS = {"instructions", "jd_text", "tracked_terms"}


class CoachProviderError(Exception):
    pass


def select_provider_name() -> str:
    provider = os.environ.get("COACH_PROVIDER", "mocked").strip().lower()
    if provider == "live":
        return "live"
    return "mocked"


def get_mocked_response(payload: dict[str, Any]) -> dict[str, Any]:
    return ai_career_coach.build_mocked_career_coach_response(payload)


def get_live_response(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("COACH_API_KEY")
    if not api_key:
        raise CoachProviderError("API key not configured")

    prompt = ai_career_coach.build_controlled_prompt(payload)
    request_body = json.dumps(
        {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        },
    ).encode("utf-8")
    request = urllib.request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=request_body,
        headers={
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=LIVE_PROVIDER_TIMEOUT_SECONDS,
        ) as response:
            response_body = response.read().decode("utf-8")
    except TimeoutError as exc:
        raise CoachProviderError("Provider timeout") from exc
    except socket.timeout as exc:
        raise CoachProviderError("Provider timeout") from exc
    except urllib.error.HTTPError as exc:
        raise CoachProviderError("Provider HTTP error") from exc
    except urllib.error.URLError as exc:
        raise CoachProviderError("Provider HTTP error") from exc
    except UnicodeDecodeError as exc:
        raise CoachProviderError("Invalid provider response") from exc

    try:
        provider_json = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise CoachProviderError("Invalid provider JSON") from exc

    response_text = _extract_text_content(provider_json)
    if len(response_text) > MAX_PROVIDER_RESPONSE_TEXT_LENGTH:
        raise CoachProviderError("Provider response too large")

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise CoachProviderError("Provider response not JSON object") from exc

    if not isinstance(parsed, dict):
        raise CoachProviderError("Provider response not JSON object")
    return parsed


def get_provider_response(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    provider_name = select_provider_name()
    if provider_name == "live":
        return provider_name, get_live_response(payload)
    return "mocked", get_mocked_response(payload)


def get_jd_enrichment_mocked_response(payload: dict[str, Any]) -> dict[str, Any]:
    jd_text = str(payload.get("jd_text") or "")
    candidates = build_mocked_enrichment_candidates(jd_text)
    return {
        "candidates": [candidate.__dict__ for candidate in candidates],
        "safety_wording": list(REQUIRED_ENRICHMENT_SAFETY_WORDING),
    }


def _build_jd_enrichment_prompt(payload: dict[str, Any]) -> str:
    safe_payload = {
        key: payload.get(key, [] if key != "jd_text" else "")
        for key in sorted(JD_ENRICHMENT_ALLOWED_PAYLOAD_KEYS)
    }
    payload_json = json.dumps(safe_payload, sort_keys=True, separators=(",", ":"))
    return (
        "JD Requirement Enrichment contract.\n"
        "Use only the supplied sanitised JD text and tracked terms.\n"
        "Return JSON only with a candidates list using the exact Phase A schema.\n"
        "Every accepted candidate must include an exact excerpt from the supplied JD text.\n"
        f"Payload JSON:\n{payload_json}"
    )


def get_jd_enrichment_live_response(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("COACH_API_KEY")
    if not api_key:
        raise CoachProviderError("API key not configured")

    prompt = _build_jd_enrichment_prompt(payload)
    request_body = json.dumps(
        {
            "model": ANTHROPIC_MODEL,
            "max_tokens": 1000,
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        },
    ).encode("utf-8")
    request = urllib.request.Request(
        ANTHROPIC_MESSAGES_URL,
        data=request_body,
        headers={
            "anthropic-version": ANTHROPIC_VERSION,
            "content-type": "application/json",
            "x-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=LIVE_PROVIDER_TIMEOUT_SECONDS,
        ) as response:
            response_body = response.read().decode("utf-8")
    except TimeoutError as exc:
        raise CoachProviderError("Provider timeout") from exc
    except socket.timeout as exc:
        raise CoachProviderError("Provider timeout") from exc
    except urllib.error.HTTPError as exc:
        raise CoachProviderError("Provider HTTP error") from exc
    except urllib.error.URLError as exc:
        raise CoachProviderError("Provider HTTP error") from exc
    except UnicodeDecodeError as exc:
        raise CoachProviderError("Invalid provider response") from exc

    try:
        provider_json = json.loads(response_body)
    except json.JSONDecodeError as exc:
        raise CoachProviderError("Invalid provider JSON") from exc

    response_text = _extract_text_content(provider_json)
    if len(response_text) > MAX_PROVIDER_RESPONSE_TEXT_LENGTH:
        raise CoachProviderError("Provider response too large")

    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError as exc:
        raise CoachProviderError("Provider response not JSON object") from exc

    if not isinstance(parsed, dict):
        raise CoachProviderError("Provider response not JSON object")
    return parsed


def get_jd_enrichment_provider_response(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    provider_name = select_provider_name()
    if provider_name == "live":
        return provider_name, get_jd_enrichment_live_response(payload)
    return "mocked", get_jd_enrichment_mocked_response(payload)


def _extract_text_content(provider_json: dict[str, Any]) -> str:
    content = provider_json.get("content")
    if not isinstance(content, list):
        raise CoachProviderError("Provider response missing text content")
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str) and text.strip():
                return text
    raise CoachProviderError("Provider response missing text content")
