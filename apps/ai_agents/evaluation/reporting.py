"""External reporting helpers for Phase 2B evaluation."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from django.conf import settings

from .runner import EvaluationRunResult

RESULTS_SCHEMA_VERSION = "p1-phase2b-results-v1"
PHASE_ID = "p1-phase2b"


class PathBoundaryError(ValueError):
    """Raised when a path resolves inside the repository."""


def repository_root() -> Path:
    return Path(settings.BASE_DIR).expanduser().resolve()


def ensure_outside_repository(path: Path, *, label: str) -> Path:
    resolved = path.expanduser().resolve()
    root = repository_root()
    if resolved == root or root in resolved.parents:
        raise PathBoundaryError(
            f"{label} must resolve outside the repository root."
        )
    return resolved


def atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def case_result_dict(result) -> dict[str, Any]:
    return {
        "case_id": result.case_id,
        "surface": result.surface,
        "result_type": result.result_type,
        "outcome": result.outcome,
        "parser_status": result.parser_status,
        "human_groundedness": result.human_groundedness,
        "breach_codes": list(result.breach_codes),
        "safe_error_category": result.safe_error_category,
        "prompt_contract_hash": result.prompt_contract_hash,
    }


def build_results_document(
    run: EvaluationRunResult,
    *,
    generated_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": RESULTS_SCHEMA_VERSION,
        "phase": PHASE_ID,
        "mode": run.mode,
        "generated_at": generated_at,
        "case_set_hash": run.case_set_hash,
        "prompt_contract_hashes": dict(sorted(run.prompt_contract_hashes.items())),
        "prompt_contract_hash_limitation": run.prompt_contract_hash_limitation,
        "case_count": run.case_count,
        "pass_count": run.pass_count,
        "fail_count": run.fail_count,
        "review_required_count": run.review_required_count,
        "hard_breach_counts": run.hard_breach_counts,
        "overall_result": run.overall_result,
        "partial": run.partial,
        "results": [case_result_dict(item) for item in run.results],
    }


def build_summary_text(document: dict[str, Any]) -> str:
    lines = [
        "CareerFunnel P1 Phase 2B evaluation summary",
        f"mode={document['mode']}",
        f"overall_result={document['overall_result']}",
        f"case_count={document['case_count']}",
        f"pass_count={document['pass_count']}",
        f"fail_count={document['fail_count']}",
        f"review_required_count={document['review_required_count']}",
        f"case_set_hash={document['case_set_hash']}",
        f"generated_at={document['generated_at']}",
        f"partial={document.get('partial', False)}",
        "prompt_contract_hash_limitation="
        f"{document['prompt_contract_hash_limitation']}",
    ]
    return "\n".join(lines) + "\n"


def write_evaluation_reports(
    run: EvaluationRunResult,
    *,
    output_dir: Path,
    generated_at: str,
) -> tuple[Path, Path]:
    resolved_dir = ensure_outside_repository(output_dir, label="output_dir")
    resolved_dir.mkdir(parents=True, exist_ok=True)
    document = build_results_document(run, generated_at=generated_at)
    results_path = resolved_dir / "evaluation_results.json"
    summary_path = resolved_dir / "evaluation_summary.txt"
    atomic_write_text(
        results_path,
        json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
    )
    atomic_write_text(summary_path, build_summary_text(document))
    return results_path, summary_path
