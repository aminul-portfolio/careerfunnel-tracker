"""Write offline Skill Ledger tool-assistant evaluation reports."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.skill_ledger.evaluation.tool_assistant_runner import (
    evaluation_report_to_json_dict,
    run_tool_assistant_evaluation,
)

RESULTS_FILENAME = "tool_assistant_evaluation_results.json"
SUMMARY_FILENAME = "tool_assistant_evaluation_summary.txt"


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
        "CareerFunnel Sprint 121 Skill Ledger tool-assistant evaluation summary",
        f"overall_result={report.overall_result}",
        f"total_case_count={report.total_case_count}",
        f"passed_case_count={report.passed_case_count}",
        f"failed_case_count={report.failed_case_count}",
        f"case_set_sha256={report.case_set_sha256}",
        f"report_sha256={report.report_sha256}",
        f"network_call_count={report.network_call_count}",
        f"live_provider_call_count={report.live_provider_call_count}",
        "",
    ]
    return "\n".join(lines)


class Command(BaseCommand):
    help = (
        "Run Sprint 121 offline Skill Ledger tool-assistant evaluation. "
        "Optional --output-dir writes deterministic JSON/TXT reports outside "
        "the repository. All synthetic evaluation database rows are rolled back."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            required=False,
            default=None,
            help=(
                "Optional absolute path to an existing directory outside the "
                "repository. Writes tool_assistant_evaluation_results.json and "
                "tool_assistant_evaluation_summary.txt."
            ),
        )

    def handle(self, *args, **options):
        output_dir = None
        results_path = None
        summary_path = None
        if options.get("output_dir"):
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
            report = run_tool_assistant_evaluation()
            payload = evaluation_report_to_json_dict(report)
            summary_text = _format_summary(report)
            transaction.set_rollback(True)

        if report is None or payload is None or summary_text is None:
            raise CommandError("evaluation failed to produce an in-memory report.")

        final_line = (
            "Offline tool-assistant evaluation complete: "
            f"overall_result={report.overall_result}; "
            f"total={report.total_case_count}; "
            f"passed={report.passed_case_count}; "
            f"failed={report.failed_case_count}; "
            f"case_set_sha256={report.case_set_sha256}; "
            f"report_sha256={report.report_sha256}"
        )

        if report.overall_result != "PASS":
            raise CommandError(final_line)

        if output_dir is not None and results_path is not None and summary_path is not None:
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

        self.stdout.write(self.style.SUCCESS(final_line))
