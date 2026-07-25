"""Minimal provider callable contract for CareerFunnel AI explanation surfaces."""

from __future__ import annotations

from typing import Protocol


class ExplanationProvider(Protocol):
    """Callable contract: structured dict in, structured dict out."""

    def __call__(self, payload: dict) -> dict: ...
