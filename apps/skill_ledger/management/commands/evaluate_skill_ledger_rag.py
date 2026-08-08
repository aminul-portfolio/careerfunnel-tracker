"""Write offline Skill Ledger RAG evaluation reports outside the repository."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.skill_ledger.evaluation.rag_evaluation_runner import (
    final_evaluation_report_to_json_dict,
    run_final_rag_evaluation,
)

RESULTS_FILENAME = "rag_evaluation_results.json"
SUMMARY_FILENAME = "rag_evaluation_summary.txt"


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
        "CareerFunnel Sprint 120 Skill Ledger RAG evaluation summary",
        f"overall_result={report.overall_result}",
        f"total_case_count={report.total_case_count}",
        f"passed_case_count={report.passed_case_count}",
        f"failed_case_count={report.failed_case_count}",
        f"case_set_sha256={report.case_set_sha256}",
        f"report_sha256={report.report_sha256}",
        f"retrieval_quality_case_count={report.retrieval_quality_case_count}",
        f"adversarial_retrieval_case_count={report.adversarial_retrieval_case_count}",
        f"attribution_safety_case_count={report.attribution_safety_case_count}",
        f"unsupported_output_case_count={report.unsupported_output_case_count}",
        f"zero_evidence_case_count={report.zero_evidence_case_count}",
        f"prompt_injection_case_count={report.prompt_injection_case_count}",
        f"network_call_count={report.network_call_count}",
        f"live_embedding_call_count={report.live_embedding_call_count}",
        f"live_llm_call_count={report.live_llm_call_count}",
        "",
    ]
    return "\n".join(lines)


class Command(BaseCommand):
    help = (
        "Run Sprint 120 offline Skill Ledger RAG evaluation and write "
        "deterministic JSON/TXT reports outside the repository. "
        "All synthetic evaluation database rows are rolled back."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            required=True,
            help=(
                "Absolute path to an existing directory outside the repository. "
                "Writes rag_evaluation_results.json and rag_evaluation_summary.txt."
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

        report = None
        payload = None
        summary_text = None
        with transaction.atomic():
            report = run_final_rag_evaluation()
            payload = final_evaluation_report_to_json_dict(report)
            summary_text = _format_summary(report)
            transaction.set_rollback(True)

        if report is None or payload is None or summary_text is None:
            raise CommandError("evaluation failed to produce an in-memory report.")

        if report.overall_result != "PASS":
            raise CommandError(
                "Offline RAG evaluation failed: "
                f"overall_result={report.overall_result}; "
                f"total={report.total_case_count}; "
                f"passed={report.passed_case_count}; "
                f"failed={report.failed_case_count}; "
                f"case_set_sha256={report.case_set_sha256}; "
                f"report_sha256={report.report_sha256}."
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
                "Offline RAG evaluation complete: "
                f"overall_result={report.overall_result}; "
                f"total={report.total_case_count}; "
                f"passed={report.passed_case_count}; "
                f"failed={report.failed_case_count}; "
                f"case_set_sha256={report.case_set_sha256}; "
                f"report_sha256={report.report_sha256}."
            )
        )
