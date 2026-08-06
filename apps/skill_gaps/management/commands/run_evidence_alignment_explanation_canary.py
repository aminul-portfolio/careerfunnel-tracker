"""Operator-only Sprint 116 evidence-alignment explanation live-canary command.

Readiness-only and single-call execution modes. No web route. No retries.
Raw evidence and redacted reports are written only outside the repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.ai_agents.claude_provider import CLAUDE_MODEL, ClaudeTelemetryResult
from apps.ai_agents.evaluation.live_runner import calculate_token_cost
from apps.ai_agents.provider_factory import (
    compose_evidence_alignment_explanation_telemetry_provider,
    live_providers_permitted,
)
from apps.skill_gaps.live_evaluation import (
    contract_manifest_sha256,
    run_evidence_alignment_explanation_canary,
)
from apps.skill_gaps.live_evaluation import (
    evidence_alignment_explanation_canary_runner as runner_module,
)
from apps.skill_gaps.live_evaluation.evidence_alignment_explanation_canary_runner import (
    EvidenceAlignmentCanaryOutcome,
    EvidenceAlignmentCanaryRunResult,
)

CONFIRMATION_VALUE = "I_ACCEPT_ONE_BILLABLE_SYNTHETIC_CANARY_CALL"
REQUIRED_CALL_CAP = 1
REQUIRED_MONETARY_CEILING_USD = Decimal("0.05")
RETENTION_INSTRUCTION = (
    "Raw provider evidence is restricted and must be manually deleted within 30 days."
)
SCHEMA_VERSION = "sprint-116-evidence-alignment-canary-v1"
RAW_FILENAME = "evidence_alignment_canary_raw_response.json"
RESULTS_FILENAME = "evidence_alignment_canary_results.json"
SUMMARY_FILENAME = "evidence_alignment_canary_summary.txt"
READINESS_FILENAME = "evidence_alignment_canary_readiness.json"
CANARY_SETTING_NAME = "AI_EVIDENCE_ALIGNMENT_EXPLANATION_LIVE_CANARY_ENABLED"

_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
_API_KEY_LIKE_RE = re.compile(
    r"(?:sk-ant-|Bearer\s+|api[_-]?key\s*[:=])",
    re.I,
)

_PASS_OUTCOMES = frozenset(
    {
        EvidenceAlignmentCanaryOutcome.INTEGRATION_SUCCESS_OUTPUT_ACCEPTED,
        EvidenceAlignmentCanaryOutcome.CONTROL_PASS_OUTPUT_SAFELY_REJECTED,
    }
)


@dataclass(frozen=True, slots=True)
class GitRepositoryState:
    branch: str
    head_sha: str
    worktree_clean: bool
    index_clean: bool
    untracked_clean: bool
    head_is_commit: bool


@dataclass(frozen=True, slots=True)
class DirectoryGateResult:
    output_directory_valid: bool
    raw_directory_valid: bool
    directories_separate: bool
    directories_external: bool
    failure_category: str | None = None


@dataclass(frozen=True, slots=True)
class CanaryReadinessReport:
    schema_version: str
    readiness_result: str
    branch_match: bool
    head_match: bool
    repository_clean: bool
    index_clean: bool
    untracked_clean: bool
    output_directory_valid: bool
    raw_directory_valid: bool
    directories_separate: bool
    directories_external: bool
    call_cap_valid: bool
    monetary_ceiling_valid: bool
    canary_setting_enabled: bool
    live_provider_mode_permitted: bool
    contract_manifest_hash_match: bool
    request_payload_hash_match: bool
    hashes_are_distinct: bool
    confirmation_required_for_execution: bool
    confirmation_valid: bool
    checked_at_utc: str
    failure_category: str | None = None


def repository_root() -> Path:
    return Path(settings.BASE_DIR).expanduser().resolve()


def _run_git(args: list[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        check=False,
        capture_output=True,
        text=True,
        shell=False,
    )
    if completed.returncode != 0:
        raise CommandError("git_inspection_failure")
    return completed.stdout.strip()


def inspect_git_repository(repo_root: Path | None = None) -> GitRepositoryState:
    root = (repo_root or repository_root()).resolve()
    branch = _run_git(["branch", "--show-current"], cwd=root)
    head_sha = _run_git(["rev-parse", "HEAD"], cwd=root).lower()
    object_type = _run_git(["cat-file", "-t", "HEAD"], cwd=root)
    porcelain = _run_git(
        ["status", "--porcelain", "--untracked-files=all"],
        cwd=root,
    )
    worktree_clean = True
    index_clean = True
    untracked_clean = True
    if porcelain:
        for line in porcelain.splitlines():
            if not line:
                continue
            if line.startswith("??"):
                untracked_clean = False
                continue
            index_status = line[0] if len(line) >= 1 else " "
            worktree_status = line[1] if len(line) >= 2 else " "
            if index_status not in {" ", "?"}:
                index_clean = False
            if worktree_status not in {" ", "?"}:
                worktree_clean = False
            if line.startswith("R ") or line.startswith("R\t"):
                index_clean = False
    return GitRepositoryState(
        branch=branch,
        head_sha=head_sha,
        worktree_clean=worktree_clean,
        index_clean=index_clean,
        untracked_clean=untracked_clean,
        head_is_commit=object_type == "commit",
    )


def authoritative_request_payload_sha256() -> str:
    """Independently hash the same production request kwargs the Phase 2 runner uses."""

    from apps.ai_agents.claude_provider import hash_request_payload

    _payload, request_kwargs, _outcome = (
        runner_module._build_authoritative_payload_and_request()
    )
    return hash_request_payload(request_kwargs)


def authoritative_production_request_kwargs() -> dict[str, Any]:
    """Return the exact production request kwargs used for the canary request hash."""

    _payload, request_kwargs, _outcome = (
        runner_module._build_authoritative_payload_and_request()
    )
    return request_kwargs


def _extract_text_fragments(value: object) -> tuple[str, ...]:
    fragments: list[str] = []
    if isinstance(value, str):
        if value:
            fragments.append(value)
        return tuple(fragments)
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str) and text:
            fragments.append(text)
        content = value.get("content")
        if content is not None and content is not value:
            fragments.extend(_extract_text_fragments(content))
        return tuple(fragments)
    if isinstance(value, (list, tuple)):
        for item in value:
            fragments.extend(_extract_text_fragments(item))
        return tuple(fragments)
    return ()


def production_request_message_contents(
    request_kwargs: dict[str, Any] | None = None,
) -> tuple[str, ...]:
    """Immutable non-empty system and message contents from production request kwargs."""

    kwargs = (
        request_kwargs
        if request_kwargs is not None
        else authoritative_production_request_kwargs()
    )
    collected: list[str] = []
    seen: set[str] = set()
    for fragment in _extract_text_fragments(kwargs.get("system")):
        if fragment not in seen:
            seen.add(fragment)
            collected.append(fragment)
    for message in kwargs.get("messages") or ():
        for fragment in _extract_text_fragments(message):
            if fragment not in seen:
                seen.add(fragment)
                collected.append(fragment)
    return tuple(collected)


def assert_final_repository_state(
    *,
    expected_branch: str,
    expected_head_sha: str,
    git_state: GitRepositoryState | None = None,
) -> None:
    """Fail closed when repository state drifts during the command."""

    state = git_state if git_state is not None else inspect_git_repository()
    expected_head = expected_head_sha.lower()
    if (
        state.branch != expected_branch
        or state.head_sha != expected_head
        or not state.worktree_clean
        or not state.index_clean
        or not state.untracked_clean
        or not state.head_is_commit
    ):
        raise CommandError("repository_state_changed")


_IO_EXCEPTION_TYPES = (
    OSError,
    IOError,
    PermissionError,
    FileNotFoundError,
    TimeoutError,
    UnicodeError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


def atomic_write_new_text(path: Path, content: str) -> None:
    """Atomically write a new UTF-8 file. Parent must exist. Do not overwrite."""

    if path.exists() or _is_symlink(path):
        raise CommandError("output_file_already_exists")
    parent = path.parent
    if not parent.is_dir():
        raise CommandError("output_parent_missing")
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(parent),
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


def write_json_document(path: Path, document: dict[str, Any]) -> None:
    text = json.dumps(
        document,
        sort_keys=True,
        indent=2,
        ensure_ascii=True,
    )
    if not text.endswith("\n"):
        text = f"{text}\n"
    atomic_write_new_text(path, text)


def write_readiness_report(path: Path, document: dict[str, Any]) -> None:
    try:
        write_json_document(path, document)
    except CommandError as exc:
        if str(exc) in {"output_file_already_exists", "output_parent_missing"}:
            raise
        raise CommandError("readiness_report_write_failure") from None
    except _IO_EXCEPTION_TYPES:
        raise CommandError("readiness_report_write_failure") from None


def write_raw_evidence_document(path: Path, document: dict[str, Any]) -> None:
    try:
        write_json_document(path, document)
    except CommandError as exc:
        if str(exc) in {"output_file_already_exists", "output_parent_missing"}:
            raise
        raise CommandError("raw_evidence_write_failure") from None
    except _IO_EXCEPTION_TYPES:
        raise CommandError("raw_evidence_write_failure") from None


def write_redacted_reports(
    *,
    results_path: Path,
    summary_path: Path,
    redacted: dict[str, Any],
    summary_text: str,
) -> None:
    try:
        write_json_document(results_path, redacted)
        atomic_write_new_text(summary_path, summary_text)
    except CommandError as exc:
        if str(exc) in {"output_file_already_exists", "output_parent_missing"}:
            raise
        raise CommandError("redacted_report_write_failure") from None
    except _IO_EXCEPTION_TYPES:
        raise CommandError("redacted_report_write_failure") from None


def read_redacted_reports(
    *,
    results_path: Path,
    summary_path: Path,
) -> tuple[str, str]:
    try:
        results_on_disk = results_path.read_text(encoding="utf-8")
        summary_on_disk = summary_path.read_text(encoding="utf-8")
    except _IO_EXCEPTION_TYPES:
        raise CommandError("redacted_report_read_failure") from None
    return results_on_disk, summary_on_disk


def validate_raw_serialisation_for_write(
    telemetry: object,
    *,
    raw_response_sha256: object,
) -> tuple[str | None, str | None]:
    """Return (error_category, serialised) without encoding invalid values."""

    if not isinstance(telemetry, ClaudeTelemetryResult):
        return "raw_evidence_unavailable", None
    serialised = telemetry.serialised_raw_response
    if not isinstance(serialised, str) or not serialised:
        return "raw_response_serialisation_unavailable", None
    if (
        not isinstance(raw_response_sha256, str)
        or _HEX64_RE.fullmatch(raw_response_sha256) is None
    ):
        return "raw_response_hash_recheck_mismatch", serialised
    return None, serialised


def scan_redacted_reports_for_leakage(
    *,
    results_text: str,
    summary_text: str,
    serialised_raw_response: str | None,
    raw_request_id: str | None,
    repository_path: Path,
    raw_evidence_dir: Path,
    request_message_contents: tuple[str, ...] = (),
) -> str | None:
    """Deterministic fail-closed leakage scan. Returns a stable category or None."""

    combined = f"{results_text}\n{summary_text}"
    if serialised_raw_response and serialised_raw_response in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    if raw_request_id and raw_request_id in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    for content in request_message_contents:
        if content and content in combined:
            return "REDACTED_REPORT_LEAKAGE_DETECTED"
    if _API_KEY_LIKE_RE.search(combined) is not None:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    if "sk-ant-" in combined or "Bearer " in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    api_key_env_name = "_".join(("ANTHROPIC", "API", "KEY"))
    if api_key_env_name in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    if "system prompt" in combined.lower() or "developer message" in combined.lower():
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    if _EMAIL_RE.search(combined) is not None:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    repo_text = str(repository_path.resolve())
    raw_text = str(raw_evidence_dir.resolve())
    if repo_text and repo_text in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    if raw_text and raw_text in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    if "Traceback (most recent call last)" in combined or "Traceback" in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    environ_marker = "os" + "." + "environ"
    if environ_marker in combined or "environ={" in combined:
        return "REDACTED_REPORT_LEAKAGE_DETECTED"
    return None


def _is_symlink(path: Path) -> bool:
    try:
        return path.is_symlink()
    except OSError:
        return False


def _directory_is_empty(path: Path) -> bool:
    try:
        next(path.iterdir())
    except StopIteration:
        return True
    except OSError:
        return False
    return False


def _paths_nested_or_equal(left: Path, right: Path) -> bool:
    if left == right:
        return True
    return left in right.parents or right in left.parents


def validate_evidence_directories(
    output_dir: Path,
    raw_evidence_dir: Path,
    *,
    repo_root: Path | None = None,
) -> tuple[Path, Path, DirectoryGateResult]:
    root = (repo_root or repository_root()).resolve()
    failure: str | None = None

    if not output_dir.is_absolute() or not raw_evidence_dir.is_absolute():
        failure = "evidence_directory_not_absolute"
    try:
        resolved_output = output_dir.expanduser().resolve(strict=True)
        resolved_raw = raw_evidence_dir.expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError):
        resolved_output = output_dir
        resolved_raw = raw_evidence_dir
        failure = failure or "evidence_directory_missing"

    output_valid = False
    raw_valid = False
    separate = False
    external = False

    if failure is None:
        if _is_symlink(output_dir) or _is_symlink(raw_evidence_dir):
            failure = "evidence_directory_symlink"
        elif not resolved_output.is_dir() or not resolved_raw.is_dir():
            failure = "evidence_directory_not_directory"
        else:
            output_valid = True
            raw_valid = True
            if _paths_nested_or_equal(resolved_output, resolved_raw):
                failure = "evidence_directories_nested_or_equal"
            else:
                separate = True
            repo_inside_output = _paths_nested_or_equal(root, resolved_output)
            repo_inside_raw = _paths_nested_or_equal(root, resolved_raw)
            output_inside_repo = resolved_output == root or root in resolved_output.parents
            raw_inside_repo = resolved_raw == root or root in resolved_raw.parents
            if (
                repo_inside_output
                or repo_inside_raw
                or output_inside_repo
                or raw_inside_repo
            ):
                failure = "evidence_directory_inside_repository"
                external = False
            else:
                external = True
            if failure is None and (
                not _directory_is_empty(resolved_output)
                or not _directory_is_empty(resolved_raw)
            ):
                failure = "evidence_directory_not_empty"
                output_valid = _directory_is_empty(resolved_output)
                raw_valid = _directory_is_empty(resolved_raw)

    gate = DirectoryGateResult(
        output_directory_valid=output_valid and failure is None,
        raw_directory_valid=raw_valid and failure is None,
        directories_separate=separate and failure != "evidence_directories_nested_or_equal",
        directories_external=external and failure != "evidence_directory_inside_repository",
        failure_category=failure,
    )
    if failure is not None:
        return output_dir, raw_evidence_dir, gate
    return resolved_output, resolved_raw, gate


def parse_monetary_ceiling(raw_value: object) -> Decimal:
    if raw_value is None:
        raise CommandError("invalid_monetary_ceiling")
    try:
        value = Decimal(str(raw_value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise CommandError("invalid_monetary_ceiling") from exc
    if not value.is_finite() or value.is_nan() or value.copy_abs() != value:
        raise CommandError("invalid_monetary_ceiling")
    if value != REQUIRED_MONETARY_CEILING_USD:
        raise CommandError("monetary_ceiling_mismatch")
    return value


def validate_sha40(value: object, *, category: str) -> str:
    if not isinstance(value, str) or _HEX40_RE.fullmatch(value) is None:
        raise CommandError(category)
    return value


def validate_sha64(value: object, *, category: str) -> str:
    if not isinstance(value, str) or _HEX64_RE.fullmatch(value) is None:
        raise CommandError(category)
    return value


def evaluate_canary_readiness(
    *,
    expected_branch: str,
    expected_head_sha: str,
    expected_contract_manifest_sha256: str,
    expected_request_payload_sha256: str,
    call_cap: int,
    monetary_ceiling_usd: object,
    confirm: str | None,
    readiness_only: bool,
    output_dir: Path,
    raw_evidence_dir: Path,
    git_state: GitRepositoryState | None = None,
    contract_hash: str | None = None,
    request_hash: str | None = None,
    canary_setting_enabled: bool | None = None,
    live_mode_permitted: bool | None = None,
    checked_at_utc: str | None = None,
    repo_root: Path | None = None,
) -> CanaryReadinessReport:
    """Evaluate every pre-call gate that does not require provider composition."""

    root = (repo_root or repository_root()).resolve()
    state = git_state or inspect_git_repository(root)
    actual_contract = contract_hash if contract_hash is not None else contract_manifest_sha256()
    actual_request = (
        request_hash
        if request_hash is not None
        else authoritative_request_payload_sha256()
    )
    setting_enabled = (
        bool(getattr(settings, CANARY_SETTING_NAME, False))
        if canary_setting_enabled is None
        else canary_setting_enabled
    )
    live_permitted = (
        live_providers_permitted()
        if live_mode_permitted is None
        else live_mode_permitted
    )
    checked_at = checked_at_utc or datetime.now(timezone.utc).isoformat()

    failure: str | None = None

    try:
        expected_head = validate_sha40(
            expected_head_sha,
            category="expected_head_sha_invalid",
        )
    except CommandError as exc:
        failure = str(exc)
        expected_head = str(expected_head_sha)

    try:
        expected_contract = validate_sha64(
            expected_contract_manifest_sha256,
            category="expected_contract_manifest_sha256_invalid",
        )
    except CommandError as exc:
        failure = failure or str(exc)
        expected_contract = str(expected_contract_manifest_sha256)

    try:
        expected_request = validate_sha64(
            expected_request_payload_sha256,
            category="expected_request_payload_sha256_invalid",
        )
    except CommandError as exc:
        failure = failure or str(exc)
        expected_request = str(expected_request_payload_sha256)

    branch_match = state.branch == expected_branch
    head_match = state.head_sha == expected_head and state.head_is_commit
    repository_clean = state.worktree_clean
    index_clean = state.index_clean
    untracked_clean = state.untracked_clean

    _resolved_output, _resolved_raw, dir_gate = validate_evidence_directories(
        output_dir,
        raw_evidence_dir,
        repo_root=root,
    )

    call_cap_valid = call_cap == REQUIRED_CALL_CAP
    monetary_ceiling_valid = False
    try:
        parse_monetary_ceiling(monetary_ceiling_usd)
        monetary_ceiling_valid = True
    except CommandError as exc:
        failure = failure or str(exc)

    contract_match = (
        _HEX64_RE.fullmatch(actual_contract) is not None
        and actual_contract == expected_contract
    )
    request_match = (
        _HEX64_RE.fullmatch(actual_request) is not None
        and actual_request == expected_request
    )
    hashes_distinct = actual_contract != actual_request

    confirmation_required = not readiness_only
    confirmation_valid = (
        True
        if readiness_only
        else isinstance(confirm, str) and confirm == CONFIRMATION_VALUE
    )

    if failure is None:
        if not branch_match:
            failure = "branch_mismatch"
        elif not head_match:
            failure = "head_mismatch"
        elif not repository_clean:
            failure = "worktree_dirty"
        elif not index_clean:
            failure = "index_dirty"
        elif not untracked_clean:
            failure = "untracked_files_present"
        elif not state.head_is_commit:
            failure = "head_not_commit"
        elif dir_gate.failure_category is not None:
            failure = dir_gate.failure_category
        elif not call_cap_valid:
            failure = "call_cap_mismatch"
        elif not monetary_ceiling_valid:
            failure = "monetary_ceiling_mismatch"
        elif not setting_enabled:
            failure = "canary_setting_disabled"
        elif not live_permitted:
            failure = "live_provider_mode_not_permitted"
        elif not contract_match:
            failure = "contract_manifest_hash_mismatch"
        elif not request_match:
            failure = "request_payload_hash_mismatch"
        elif not hashes_distinct:
            failure = "hash_type_collision"
        elif confirmation_required and not confirmation_valid:
            failure = "confirmation_rejected"

    return CanaryReadinessReport(
        schema_version=SCHEMA_VERSION,
        readiness_result="PASS" if failure is None else "FAIL",
        branch_match=branch_match,
        head_match=head_match,
        repository_clean=repository_clean,
        index_clean=index_clean,
        untracked_clean=untracked_clean,
        output_directory_valid=dir_gate.output_directory_valid,
        raw_directory_valid=dir_gate.raw_directory_valid,
        directories_separate=dir_gate.directories_separate,
        directories_external=dir_gate.directories_external,
        call_cap_valid=call_cap_valid,
        monetary_ceiling_valid=monetary_ceiling_valid,
        canary_setting_enabled=setting_enabled,
        live_provider_mode_permitted=live_permitted,
        contract_manifest_hash_match=contract_match,
        request_payload_hash_match=request_match,
        hashes_are_distinct=hashes_distinct,
        confirmation_required_for_execution=confirmation_required,
        confirmation_valid=confirmation_valid,
        checked_at_utc=checked_at,
        failure_category=failure,
    )


def assess_spend(
    result: EvidenceAlignmentCanaryRunResult,
) -> tuple[str, Decimal | None]:
    """Reuse P1 pricing constants via calculate_token_cost for the locked model."""

    if result.returned_model != CLAUDE_MODEL:
        return "INCOMPLETE", None
    if not isinstance(result.input_tokens, int) or not isinstance(
        result.output_tokens,
        int,
    ):
        return "INCOMPLETE", None
    if result.input_tokens < 0 or result.output_tokens < 0:
        return "INCOMPLETE", None
    spend = calculate_token_cost(
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )
    return "COMPLETE", spend


def overall_result_for_outcome(outcome: EvidenceAlignmentCanaryOutcome) -> str:
    if outcome in _PASS_OUTCOMES:
        return "PASS"
    return "FAIL"


def build_raw_evidence_document(
    *,
    telemetry: ClaudeTelemetryResult,
    case_id: str,
    raw_response_sha256: str,
    request_payload_sha256: str,
    captured_at_utc: str,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "case_id": case_id,
        "serialised_raw_response": telemetry.serialised_raw_response,
        "raw_response_sha256": raw_response_sha256,
        "returned_model": telemetry.returned_model,
        "stop_reason": telemetry.stop_reason,
        "input_tokens": telemetry.input_tokens,
        "output_tokens": telemetry.output_tokens,
        "latency_ms": telemetry.latency_ms,
        "request_payload_sha256": request_payload_sha256,
        "captured_at_utc": captured_at_utc,
    }


def build_redacted_results_document(
    *,
    result: EvidenceAlignmentCanaryRunResult,
    overall_result: str,
    call_cap: int,
    monetary_ceiling_usd: Decimal,
    pricing_status: str,
    estimated_spend_usd: Decimal | None,
    generated_at_utc: str,
    safe_error_category: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "overall_result": overall_result,
        "run_outcome": result.outcome.value,
        "case_id": result.case_id,
        "expected_deterministic_outcome": result.expected_deterministic_outcome,
        "contract_manifest_sha256": result.contract_manifest_sha256,
        "contract_manifest_hash_match": result.contract_manifest_hash_match,
        "request_payload_sha256": result.request_payload_sha256,
        "request_payload_hash_match": result.request_payload_hash_match,
        "raw_response_sha256": result.raw_response_sha256,
        "hashes_are_distinct": result.hashes_are_distinct,
        "attempted_call_count": result.attempted_call_count,
        "completed_call_count": result.completed_call_count,
        "returned_model": result.returned_model,
        "model_match": result.model_match,
        "output_token_cap": result.output_token_cap,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "total_tokens": result.total_tokens,
        "stop_reason": result.stop_reason,
        "latency_ms": result.latency_ms,
        "parser_status": result.parser_status,
        "validator_status": result.validator_status,
        "validator_rejection_code": result.validator_rejection_code,
        "manual_review_marker_present": result.manual_review_marker_present,
        "persistence_count": result.persistence_count,
        "temperature_configuration": result.temperature_configuration,
        "temperature_source": result.temperature_source,
        "top_p_configuration": result.top_p_configuration,
        "top_k_configuration": result.top_k_configuration,
        "thinking_configuration": result.thinking_configuration,
        "accepted_explanation_summary": result.accepted_explanation_summary,
        "safe_error_category": safe_error_category or result.safe_error_category,
        "call_cap": call_cap,
        "monetary_ceiling_usd": str(monetary_ceiling_usd),
        "pricing_status": pricing_status,
        "estimated_spend_usd": (
            str(estimated_spend_usd) if estimated_spend_usd is not None else None
        ),
        "evidence_retention_instruction": RETENTION_INSTRUCTION,
        "generated_at_utc": generated_at_utc,
        "advisory_notice": (
            "One synthetic canary only. Outputs are advisory. Safety checks are "
            "bounded. Manual review remains required."
        ),
    }


def build_summary_text(document: dict[str, Any]) -> str:
    lines = [
        "CareerFunnel Sprint 116 evidence-alignment explanation canary summary",
        f"overall_result={document['overall_result']}",
        f"run_outcome={document['run_outcome']}",
        f"case_id={document['case_id']}",
        f"returned_model={document.get('returned_model')}",
        f"input_tokens={document.get('input_tokens')}",
        f"output_tokens={document.get('output_tokens')}",
        f"total_tokens={document.get('total_tokens')}",
        f"latency_ms={document.get('latency_ms')}",
        f"attempted_call_count={document.get('attempted_call_count')}",
        f"completed_call_count={document.get('completed_call_count')}",
        f"contract_manifest_hash_match={document.get('contract_manifest_hash_match')}",
        f"request_payload_hash_match={document.get('request_payload_hash_match')}",
        f"raw_response_sha256={document.get('raw_response_sha256')}",
        f"parser_status={document.get('parser_status')}",
        f"validator_status={document.get('validator_status')}",
        f"validator_rejection_code={document.get('validator_rejection_code')}",
        f"manual_review_marker_present={document.get('manual_review_marker_present')}",
        f"safe_error_category={document.get('safe_error_category')}",
        f"pricing_status={document.get('pricing_status')}",
        f"estimated_spend_usd={document.get('estimated_spend_usd')}",
        f"evidence_retention_instruction={document.get('evidence_retention_instruction')}",
        f"generated_at_utc={document.get('generated_at_utc')}",
        "advisory_notice=One synthetic canary only. Outputs are advisory. "
        "Safety checks are bounded. Manual review remains required.",
    ]
    return "\n".join(lines) + "\n"


def ensure_target_files_absent(paths: list[Path]) -> None:
    for path in paths:
        if path.exists() or _is_symlink(path):
            raise CommandError("output_file_already_exists")


def capture_once_provider(
    composed: Callable[[dict], ClaudeTelemetryResult],
    capture: dict[str, Any],
) -> Callable[[dict], ClaudeTelemetryResult]:
    def _wrapped(payload: dict) -> ClaudeTelemetryResult:
        if capture.get("call_count", 0) >= 1:
            raise RuntimeError("provider_retry_forbidden")
        capture["call_count"] = int(capture.get("call_count", 0)) + 1
        telemetry = composed(payload)
        capture["telemetry"] = telemetry
        return telemetry

    return _wrapped


class Command(BaseCommand):
    help = (
        "Run Sprint 116 evidence-alignment explanation synthetic live canary "
        "in readiness-only or single-call execution mode. Requires the dedicated "
        "canary setting, explicit confirmation for execution, external empty "
        "directories, and exact branch/HEAD/hash gates. Does not activate "
        "user-facing explanation features."
    )

    def add_arguments(self, parser):
        parser.add_argument("--output-dir", required=True)
        parser.add_argument("--raw-evidence-dir", required=True)
        parser.add_argument("--expected-branch", required=True)
        parser.add_argument("--expected-head-sha", required=True)
        parser.add_argument("--expected-contract-manifest-sha256", required=True)
        parser.add_argument("--expected-request-payload-sha256", required=True)
        parser.add_argument("--call-cap", required=True, type=int)
        parser.add_argument("--monetary-ceiling-usd", required=True)
        parser.add_argument("--confirm", required=False, default=None)
        parser.add_argument(
            "--readiness-only",
            action="store_true",
            default=False,
        )

    def handle(self, *args, **options):
        readiness_only = bool(options["readiness_only"])
        output_dir = Path(options["output_dir"])
        raw_evidence_dir = Path(options["raw_evidence_dir"])
        report = evaluate_canary_readiness(
            expected_branch=options["expected_branch"],
            expected_head_sha=options["expected_head_sha"],
            expected_contract_manifest_sha256=options[
                "expected_contract_manifest_sha256"
            ],
            expected_request_payload_sha256=options[
                "expected_request_payload_sha256"
            ],
            call_cap=options["call_cap"],
            monetary_ceiling_usd=options["monetary_ceiling_usd"],
            confirm=options.get("confirm"),
            readiness_only=readiness_only,
            output_dir=output_dir,
            raw_evidence_dir=raw_evidence_dir,
        )

        if readiness_only:
            if (
                report.output_directory_valid
                and report.raw_directory_valid
                and report.directories_separate
                and report.directories_external
            ):
                resolved_output, _resolved_raw, _gate = validate_evidence_directories(
                    output_dir,
                    raw_evidence_dir,
                )
                readiness_path = resolved_output / READINESS_FILENAME
                ensure_target_files_absent([readiness_path])
                document = {
                    key: value
                    for key, value in asdict(report).items()
                    if key != "failure_category"
                }
                document.pop("confirmation_valid", None)
                write_readiness_report(readiness_path, document)
            if report.readiness_result != "PASS":
                raise CommandError(
                    report.failure_category or "readiness_failure"
                )
            assert_final_repository_state(
                expected_branch=options["expected_branch"],
                expected_head_sha=options["expected_head_sha"],
            )
            self.stdout.write("readiness_result=PASS")
            return

        if report.readiness_result != "PASS":
            raise CommandError(report.failure_category or "readiness_failure")

        resolved_output, resolved_raw, _gate = validate_evidence_directories(
            output_dir,
            raw_evidence_dir,
        )
        results_path = resolved_output / RESULTS_FILENAME
        summary_path = resolved_output / SUMMARY_FILENAME
        raw_path = resolved_raw / RAW_FILENAME
        ensure_target_files_absent([results_path, summary_path, raw_path])

        composed = compose_evidence_alignment_explanation_telemetry_provider()
        if composed is None:
            raise CommandError("provider_composition_refused")

        capture: dict[str, Any] = {"telemetry": None, "call_count": 0}
        wrapped = capture_once_provider(composed, capture)
        ceiling = parse_monetary_ceiling(options["monetary_ceiling_usd"])
        request_message_contents = production_request_message_contents()

        result = run_evidence_alignment_explanation_canary(
            telemetry_provider=wrapped,
            expected_contract_manifest_sha256=options[
                "expected_contract_manifest_sha256"
            ],
            expected_request_payload_sha256=options[
                "expected_request_payload_sha256"
            ],
        )

        overall = overall_result_for_outcome(result.outcome)
        pricing_status, estimated_spend = assess_spend(result)
        safe_error = result.safe_error_category

        if pricing_status != "COMPLETE" or estimated_spend is None:
            overall = "FAIL"
            safe_error = safe_error or "pricing_incomplete"
        elif estimated_spend > ceiling:
            overall = "FAIL"
            safe_error = safe_error or "monetary_ceiling_exceeded"

        if result.outcome == EvidenceAlignmentCanaryOutcome.PROVIDER_FAILURE:
            if result.attempted_call_count != 1:
                overall = "FAIL"
                safe_error = safe_error or "call_count_mismatch"
        elif result.attempted_call_count != 1 or result.completed_call_count != 1:
            overall = "FAIL"
            safe_error = safe_error or "call_count_mismatch"

        telemetry = capture.get("telemetry")
        generated_at = datetime.now(timezone.utc).isoformat()
        serialisation_error, serialised = validate_raw_serialisation_for_write(
            telemetry,
            raw_response_sha256=result.raw_response_sha256,
        )
        if serialisation_error is not None:
            overall = "FAIL"
            safe_error = result.safe_error_category or serialisation_error
        elif isinstance(telemetry, ClaudeTelemetryResult) and serialised is not None:
            independent = hashlib.sha256(serialised.encode("utf-8")).hexdigest()
            if independent != result.raw_response_sha256:
                overall = "FAIL"
                safe_error = "raw_response_hash_recheck_mismatch"
            else:
                raw_document = build_raw_evidence_document(
                    telemetry=telemetry,
                    case_id=result.case_id,
                    raw_response_sha256=independent,
                    request_payload_sha256=(
                        result.request_payload_sha256
                        or options["expected_request_payload_sha256"]
                    ),
                    captured_at_utc=generated_at,
                )
                write_raw_evidence_document(raw_path, raw_document)

        redacted = build_redacted_results_document(
            result=result,
            overall_result=overall,
            call_cap=REQUIRED_CALL_CAP,
            monetary_ceiling_usd=ceiling,
            pricing_status=pricing_status,
            estimated_spend_usd=(
                estimated_spend if pricing_status == "COMPLETE" else None
            ),
            generated_at_utc=generated_at,
            safe_error_category=safe_error,
        )
        summary_text = build_summary_text(redacted)
        write_redacted_reports(
            results_path=results_path,
            summary_path=summary_path,
            redacted=redacted,
            summary_text=summary_text,
        )

        results_on_disk, summary_on_disk = read_redacted_reports(
            results_path=results_path,
            summary_path=summary_path,
        )
        leak = scan_redacted_reports_for_leakage(
            results_text=results_on_disk,
            summary_text=summary_on_disk,
            serialised_raw_response=(
                serialised
                if isinstance(serialised, str) and serialised
                else None
            ),
            raw_request_id=(
                telemetry.raw_request_id
                if isinstance(telemetry, ClaudeTelemetryResult)
                else None
            ),
            repository_path=repository_root(),
            raw_evidence_dir=resolved_raw,
            request_message_contents=request_message_contents,
        )
        if leak is not None:
            raise CommandError(leak)

        assert_final_repository_state(
            expected_branch=options["expected_branch"],
            expected_head_sha=options["expected_head_sha"],
        )

        if overall != "PASS":
            raise CommandError(safe_error or "canary_execution_failed")

        self.stdout.write(
            "overall_result=PASS "
            f"run_outcome={result.outcome.value} "
            f"case_id={result.case_id}"
        )
