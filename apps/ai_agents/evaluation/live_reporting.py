"""External live-evaluation reporting for Phase 2C (redacted + raw evidence)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from .reporting import (
    PathBoundaryError,
    atomic_write_text,
    ensure_outside_repository,
    repository_root,
)

RESULTS_SCHEMA_VERSION = "p1-phase2c-live-results-v1"
PHASE_ID = "p1-phase2c"
RAW_EVIDENCE_RETENTION_DAYS = 30


def hash_request_id(raw_request_id: str | None) -> str | None:
    if not raw_request_id:
        return None
    return hashlib.sha256(raw_request_id.encode("utf-8")).hexdigest()


def validate_external_path(path: Path, *, label: str) -> Path:
    """Canonical outside-repository check used by the live command and runner."""
    return ensure_outside_repository(path, label=label)


def ensure_output_and_raw_dirs_separate(
    output_dir: Path,
    raw_evidence_dir: Path,
) -> tuple[Path, Path]:
    """Require distinct, non-nested redacted-output and raw-evidence directories."""
    resolved_output = ensure_outside_repository(output_dir, label="output_dir")
    resolved_raw = ensure_outside_repository(
        raw_evidence_dir,
        label="raw_evidence_dir",
    )
    if resolved_output == resolved_raw:
        raise PathBoundaryError(
            "output_dir and raw_evidence_dir must resolve to different paths."
        )
    if resolved_output in resolved_raw.parents:
        raise PathBoundaryError(
            "output_dir must not be a parent of raw_evidence_dir."
        )
    if resolved_raw in resolved_output.parents:
        raise PathBoundaryError(
            "raw_evidence_dir must not be a parent of output_dir."
        )
    return resolved_output, resolved_raw


def case_live_result_dict(result: Any) -> dict[str, Any]:
    return {
        "case_id": result.case_id,
        "surface": result.surface,
        "model": result.model,
        "hashed_request_id": result.hashed_request_id,
        "stop_reason": result.stop_reason,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "latency_ms": result.latency_ms,
        "actual_cost_usd": str(result.actual_cost_usd)
        if result.actual_cost_usd is not None
        else None,
        "pricing_profile_id": result.pricing_profile_id,
        "contract_manifest_hash": result.contract_manifest_hash,
        "request_payload_hash": result.request_payload_hash,
        "raw_response_hash": result.raw_response_hash,
        "parser_status": result.parser_status,
        "outcome": result.outcome,
        "breach_codes": list(result.breach_codes),
        "safe_error_category": result.safe_error_category,
    }


def build_live_results_document(
    run: Any,
    *,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": RESULTS_SCHEMA_VERSION,
        "phase": PHASE_ID,
        "mode": "live",
        "generated_at": generated_at,
        "case_set_hash": run.case_set_hash,
        "pricing_profile_id": run.pricing_profile_id,
        "pricing_profile_effective_date": run.pricing_profile_effective_date,
        "input_unit_price_usd_per_million": str(run.input_unit_price_usd_per_million),
        "output_unit_price_usd_per_million": str(run.output_unit_price_usd_per_million),
        "monetary_ceiling_usd": str(run.monetary_ceiling_usd),
        "projected_max_cost_usd": str(run.projected_max_cost_usd),
        "actual_spend_usd": str(run.actual_spend_usd),
        "call_cap": run.call_cap,
        "calls_made": run.calls_made,
        "case_count": run.case_count,
        "pass_count": run.pass_count,
        "fail_count": run.fail_count,
        "review_required_count": run.review_required_count,
        "hard_breach_counts": dict(run.hard_breach_counts),
        "overall_result": run.overall_result,
        "stop_reason": run.stop_reason,
        "held_after_stage": run.held_after_stage,
        "partial": run.partial,
        "actual_spend_complete": run.actual_spend_complete,
        "results": [case_live_result_dict(item) for item in run.results],
    }


def build_live_summary_text(document: dict[str, Any]) -> str:
    lines = [
        "CareerFunnel P1 Phase 2C live evaluation summary",
        f"overall_result={document['overall_result']}",
        f"case_count={document['case_count']}",
        f"pass_count={document['pass_count']}",
        f"fail_count={document['fail_count']}",
        f"review_required_count={document['review_required_count']}",
        f"calls_made={document['calls_made']}",
        f"actual_spend_usd={document['actual_spend_usd']}",
        f"actual_spend_complete={document.get('actual_spend_complete', True)}",
        f"projected_max_cost_usd={document['projected_max_cost_usd']}",
        f"monetary_ceiling_usd={document['monetary_ceiling_usd']}",
        f"case_set_hash={document['case_set_hash']}",
        f"stop_reason={document.get('stop_reason')}",
        f"held_after_stage={document.get('held_after_stage')}",
        f"partial={document.get('partial', False)}",
        f"generated_at={document['generated_at']}",
    ]
    if document.get("actual_spend_complete") is False:
        lines.insert(
            8,
            "actual_spend_status=incomplete (one or more attempted provider calls "
            "could not be priced safely)",
        )
    return "\n".join(lines) + "\n"


def write_live_evaluation_reports(
    run: Any,
    *,
    output_dir: Path,
    generated_at: str,
) -> tuple[Path, Path]:
    resolved_dir = ensure_outside_repository(output_dir, label="output_dir")
    resolved_dir.mkdir(parents=True, exist_ok=True)
    document = build_live_results_document(run, generated_at=generated_at)
    results_path = resolved_dir / "live_evaluation_results.json"
    summary_path = resolved_dir / "live_evaluation_summary.txt"
    atomic_write_text(
        results_path,
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )
    atomic_write_text(summary_path, build_live_summary_text(document))
    return results_path, summary_path


def append_raw_live_evidence(
    *,
    raw_evidence_dir: Path,
    case_id: str,
    raw_request_id: str | None,
    serialised_raw_response: str,
    raw_response_hash: str,
    capture_timestamp: str | None = None,
) -> Path:
    resolved_dir = ensure_outside_repository(
        raw_evidence_dir,
        label="raw_evidence_dir",
    )
    resolved_dir.mkdir(parents=True, exist_ok=True)
    path = resolved_dir / "raw_live_evidence.jsonl"
    captured = capture_timestamp or datetime.now(timezone.utc).isoformat()
    deadline = (
        datetime.fromisoformat(captured.replace("Z", "+00:00"))
        + timedelta(days=RAW_EVIDENCE_RETENTION_DAYS)
    ).isoformat()
    record = {
        "case_id": case_id,
        "raw_request_id": raw_request_id,
        "serialised_raw_response": serialised_raw_response,
        "raw_response_hash": raw_response_hash,
        "capture_timestamp": captured,
        "retention_deadline": deadline,
        "retention_days": RAW_EVIDENCE_RETENTION_DAYS,
        "manual_deletion_required": True,
    }
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def decimal_to_str(value: Decimal) -> str:
    return format(value, "f")


__all__ = [
    "PathBoundaryError",
    "append_raw_live_evidence",
    "build_live_results_document",
    "build_live_summary_text",
    "ensure_outside_repository",
    "ensure_output_and_raw_dirs_separate",
    "hash_request_id",
    "repository_root",
    "validate_external_path",
    "write_live_evaluation_reports",
]
