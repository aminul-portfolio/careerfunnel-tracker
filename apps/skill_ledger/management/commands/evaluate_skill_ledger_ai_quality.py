"""Write offline Skill Ledger AI quality-lifecycle evaluation reports outside the repository."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.skill_ledger.evaluation.quality_runner import (
    AiQualityEvaluationRunnerError,
    evaluation_report_to_json_dict,
    run_ai_quality_evaluation,
)

RESULTS_FILENAME = "ai_quality_evaluation_results.json"
SUMMARY_FILENAME = "ai_quality_evaluation_summary.txt"


def _repository_root() -> Path:
    return Path(settings.BASE_DIR).expanduser().resolve()


def _is_inside_or_equal(candidate: Path, root: Path) -> bool:
    if candidate == root:
        return True
    return root in candidate.parents


def resolve_external_output_dir(path_value: str) -> Path:
    """Resolve and validate an absolute external output directory."""
    if not isinstance(path_value, str) or not path_value.strip():
        raise CommandError("output directory must be a non-empty string.")

    candidate = Path(path_value)
    if not candidate.is_absolute():
        raise CommandError("output directory must be absolute.")

    try:
        resolved = candidate.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise CommandError("output directory does not exist.") from exc
    except OSError as exc:
        raise CommandError(
            f"output directory could not be resolved: {exc.__class__.__name__}."
        ) from exc

    if not resolved.is_dir():
        raise CommandError("output path must be an existing directory.")

    root = _repository_root()
    if _is_inside_or_equal(resolved, root):
        raise CommandError(
            "output directory must resolve outside the repository root."
        )
    return resolved


def _format_summary(report) -> str:
    lines = [
        "CareerFunnel Sprint 122 AI quality-lifecycle evaluation summary",
        f"overall_result={report.overall_result}",
        f"total_case_count={report.total_case_count}",
        f"passed_case_count={report.passed_case_count}",
        f"failed_case_count={report.failed_case_count}",
        f"quality_case_set_sha256={report.quality_case_set_sha256}",
        f"quality_report_sha256={report.quality_report_sha256}",
        f"rag_case_set_sha256={report.rag_case_set_sha256}",
        f"tool_assistant_case_set_sha256={report.tool_assistant_case_set_sha256}",
        f"baseline_integrity_sha256={report.baseline_integrity_sha256}",
        f"network_call_count={report.network_call_count}",
        f"live_embedding_call_count={report.live_embedding_call_count}",
        f"live_llm_call_count={report.live_llm_call_count}",
        f"live_provider_call_count={report.live_provider_call_count}",
        f"candidate_sha={report.candidate_sha}",
        "",
    ]
    return "\n".join(lines)


class Command(BaseCommand):
    help = (
        "Run Sprint 122 offline AI quality-lifecycle evaluation and write "
        "deterministic JSON/TXT reports outside the repository. "
        "candidate_sha is informational only."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--candidate-sha",
            required=True,
            help=(
                "Informational candidate SHA (7..64 lowercase hex). "
                "Does not affect gate, case, or report hash semantics."
            ),
        )
        parser.add_argument(
            "--output-dir",
            required=True,
            help=(
                "Absolute path to an existing directory outside the repository. "
                "Writes ai_quality_evaluation_results.json and "
                "ai_quality_evaluation_summary.txt."
            ),
        )

    def handle(self, *args, **options):
        output_dir = resolve_external_output_dir(options["output_dir"])
        results_path = output_dir / RESULTS_FILENAME
        summary_path = output_dir / SUMMARY_FILENAME
        if results_path.exists() or summary_path.exists():
            raise CommandError(
                "output files already exist; refuse to overwrite existing reports."
            )

        try:
            report = run_ai_quality_evaluation(
                candidate_sha=options["candidate_sha"],
            )
        except AiQualityEvaluationRunnerError as exc:
            raise CommandError(str(exc)) from None

        payload = evaluation_report_to_json_dict(report)
        summary_text = _format_summary(report)

        if report.overall_result != "PASS":
            raise CommandError(
                "Offline AI quality evaluation failed: "
                f"overall_result={report.overall_result}; "
                f"total={report.total_case_count}; "
                f"passed={report.passed_case_count}; "
                f"failed={report.failed_case_count}; "
                f"quality_case_set_sha256={report.quality_case_set_sha256}; "
                f"quality_report_sha256={report.quality_report_sha256}."
            )

        results_text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        results_text = results_text.replace("\r\n", "\n").replace("\r", "\n")
        if not results_text.endswith("\n"):
            results_text = results_text + "\n"
        summary_text = summary_text.replace("\r\n", "\n").replace("\r", "\n")
        if not summary_text.endswith("\n"):
            summary_text = summary_text + "\n"

        try:
            with open(results_path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(results_text)
            with open(summary_path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(summary_text)
        except FileExistsError as exc:
            raise CommandError("output file already exists.") from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Offline AI quality evaluation complete: "
                f"overall_result={report.overall_result}; "
                f"total={report.total_case_count}; "
                f"passed={report.passed_case_count}; "
                f"failed={report.failed_case_count}; "
                f"quality_case_set_sha256={report.quality_case_set_sha256}; "
                f"quality_report_sha256={report.quality_report_sha256}."
            )
        )
