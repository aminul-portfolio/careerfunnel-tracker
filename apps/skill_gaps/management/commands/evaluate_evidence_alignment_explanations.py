"""Write offline evidence-alignment explanation evaluation reports outside the repo."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.skill_gaps.evaluation.explanation_evaluation_cases import (
    ADVERSARIAL_EVALUATION_CASES,
    GOLDEN_EVALUATION_CASES,
)
from apps.skill_gaps.evaluation.explanation_evaluation_runner import (
    evaluation_report_to_json_dict,
    run_evidence_alignment_explanation_evaluation,
)


def _repository_root() -> Path:
    return Path(settings.BASE_DIR).expanduser().resolve()


def _is_inside_or_equal(candidate: Path, root: Path) -> bool:
    if candidate == root:
        return True
    return root in candidate.parents


def resolve_external_output_file(path_value: str) -> Path:
    """Resolve and validate an absolute external output file path."""
    if not isinstance(path_value, str) or not path_value.strip():
        raise CommandError("output path must be a non-empty string.")

    candidate = Path(path_value)
    if not candidate.is_absolute():
        raise CommandError("output path must be absolute.")

    if candidate.exists() and candidate.is_dir():
        raise CommandError("output path must be a file, not a directory.")

    parent = candidate.parent
    try:
        resolved_parent = parent.expanduser().resolve(strict=True)
    except FileNotFoundError as exc:
        raise CommandError("output parent directory does not exist.") from exc
    except OSError as exc:
        raise CommandError(
            f"output parent directory could not be resolved: {exc.__class__.__name__}."
        ) from exc

    root = _repository_root()
    if _is_inside_or_equal(resolved_parent, root):
        raise CommandError(
            "output path must resolve outside the repository root."
        )

    resolved = (resolved_parent / candidate.name).resolve()
    if _is_inside_or_equal(resolved, root):
        raise CommandError(
            "output path must resolve outside the repository root."
        )

    if resolved.exists():
        if resolved.is_dir():
            raise CommandError("output path must be a file, not a directory.")
        raise CommandError("output file already exists.")

    return resolved


class Command(BaseCommand):
    help = (
        "Run Sprint 115 offline evidence-alignment explanation evaluation "
        "and write one JSON report outside the repository."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            required=True,
            help=(
                "Absolute path to a new JSON report file outside the repository. "
                "The parent directory must already exist and the file must not."
            ),
        )

    def handle(self, *args, **options):
        output_path = resolve_external_output_file(options["output"])
        cases = GOLDEN_EVALUATION_CASES + ADVERSARIAL_EVALUATION_CASES
        report = run_evidence_alignment_explanation_evaluation(cases)
        payload = evaluation_report_to_json_dict(report)
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if not text.endswith("\n"):
            text = text + "\n"

        try:
            with open(output_path, "x", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        except FileExistsError as exc:
            raise CommandError("output file already exists.") from exc

        if report.overall_result != "PASS":
            raise CommandError(
                "Offline evaluation failed: "
                f"overall_result={report.overall_result}; "
                f"total={report.total_case_count}; "
                f"passed={report.passed_case_count}; "
                f"failed={report.failed_case_count}; "
                f"case_set_sha256={report.case_set_sha256}; "
                f"report_sha256={report.report_sha256}."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Offline evaluation complete: "
                f"overall_result={report.overall_result}; "
                f"total={report.total_case_count}; "
                f"passed={report.passed_case_count}; "
                f"failed={report.failed_case_count}; "
                f"case_set_sha256={report.case_set_sha256}; "
                f"report_sha256={report.report_sha256}."
            )
        )
