"""Management command for Phase 2C controlled live AI evaluation."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.ai_agents.evaluation.cases import CaseValidationError, load_case_set
from apps.ai_agents.evaluation.live_reporting import (
    PathBoundaryError,
    append_raw_live_evidence,
    ensure_output_and_raw_dirs_separate,
    validate_external_path,
    write_live_evaluation_reports,
)
from apps.ai_agents.evaluation.live_runner import (
    MAXIMUM_CALL_CAP,
    MAXIMUM_OPERATOR_CEILING_USD,
    LiveEvaluationError,
    execute_live_evaluation_plan,
    prepare_live_evaluation_plan,
    validate_expected_case_set_hash,
    validate_monetary_ceiling_usd,
)
from apps.ai_agents.provider_factory import (
    compose_cv_tailoring_telemetry_provider,
    compose_fit_scoring_telemetry_provider,
)

CONFIRMATION_VALUE = "I_UNDERSTAND_LIVE_AI_CALLS_ARE_BILLABLE"
LIVE_FLAG_NAME = "AI_LIVE_EVALUATION_ENABLED"
LIVE_FLAG_REQUIRED_VALUE = "1"


class Command(BaseCommand):
    help = (
        "Run CareerFunnel P1 Phase 2C controlled live AI evaluation. "
        "Requires AI_LIVE_EVALUATION_ENABLED=1, explicit billable confirmation, "
        "call cap, monetary ceiling, independent case-set hash, and external "
        "paths only. Does not activate user-facing runtime providers."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--case-set",
            required=True,
            help="Absolute path to an external case-set JSON file.",
        )
        parser.add_argument(
            "--output-dir",
            required=True,
            help="Absolute path to an external redacted output directory.",
        )
        parser.add_argument(
            "--raw-evidence-dir",
            required=True,
            help="Absolute path to an external restricted raw-evidence directory.",
        )
        parser.add_argument(
            "--call-cap",
            required=True,
            type=int,
            help=f"Maximum provider calls (1-{MAXIMUM_CALL_CAP}).",
        )
        parser.add_argument(
            "--monetary-ceiling-usd",
            required=True,
            help=f"Hard USD ceiling (maximum {MAXIMUM_OPERATOR_CEILING_USD}).",
        )
        parser.add_argument(
            "--expected-case-set-hash",
            required=True,
            help="Approved external golden case-set SHA-256 hash (64 hex chars).",
        )
        parser.add_argument(
            "--confirm",
            required=True,
            help=f'Must equal "{CONFIRMATION_VALUE}".',
        )

    def handle(self, *args, **options):
        if os.environ.get(LIVE_FLAG_NAME) != LIVE_FLAG_REQUIRED_VALUE:
            raise CommandError(
                "Live evaluation is disabled. Set AI_LIVE_EVALUATION_ENABLED=1."
            )
        if options["confirm"] != CONFIRMATION_VALUE:
            raise CommandError(
                "Confirmation rejected. "
                f"Pass --confirm {CONFIRMATION_VALUE}."
            )

        call_cap = options["call_cap"]
        if call_cap < 1 or call_cap > MAXIMUM_CALL_CAP:
            raise CommandError(
                f"call-cap must be between 1 and {MAXIMUM_CALL_CAP}."
            )

        try:
            ceiling = Decimal(str(options["monetary_ceiling_usd"]))
        except (InvalidOperation, TypeError) as exc:
            raise CommandError("invalid_monetary_ceiling") from exc
        try:
            ceiling = validate_monetary_ceiling_usd(ceiling)
        except LiveEvaluationError as exc:
            raise CommandError("invalid_monetary_ceiling") from exc

        try:
            expected_hash = validate_expected_case_set_hash(
                options["expected_case_set_hash"]
            )
        except LiveEvaluationError as exc:
            raise CommandError("case_set_hash_mismatch") from exc

        try:
            case_set_path = validate_external_path(
                Path(options["case_set"]),
                label="case_set",
            )
            output_dir, raw_evidence_dir = ensure_output_and_raw_dirs_separate(
                Path(options["output_dir"]),
                Path(options["raw_evidence_dir"]),
            )
        except PathBoundaryError as exc:
            raise CommandError(str(exc)) from exc

        if not case_set_path.is_file():
            raise CommandError("Case-set path does not exist or is not a file.")

        try:
            case_set = load_case_set(case_set_path)
        except CaseValidationError as exc:
            raise CommandError(str(exc)) from exc

        try:
            plan = prepare_live_evaluation_plan(
                case_set,
                call_cap=call_cap,
                monetary_ceiling_usd=ceiling,
                expected_case_set_hash=expected_hash,
            )
        except LiveEvaluationError as exc:
            raise CommandError(str(exc)) from exc

        # Compose providers only after all gates and pure pre-flight pass.
        fit_provider = compose_fit_scoring_telemetry_provider()
        cv_provider = compose_cv_tailoring_telemetry_provider()
        if fit_provider is None or cv_provider is None:
            raise CommandError(
                "Live provider composition refused. "
                "AI_EXPLANATION_PROVIDER must be live with a configured API key."
            )

        def _write_raw(**kwargs):
            append_raw_live_evidence(raw_evidence_dir=raw_evidence_dir, **kwargs)

        try:
            run = execute_live_evaluation_plan(
                plan,
                fit_telemetry_provider=fit_provider,
                cv_telemetry_provider=cv_provider,
                raw_evidence_writer=_write_raw,
            )
            generated_at = datetime.now(timezone.utc).isoformat()
            try:
                results_path, summary_path = write_live_evaluation_reports(
                    run,
                    output_dir=output_dir,
                    generated_at=generated_at,
                )
            except Exception as exc:
                raise CommandError("report_write_failure") from exc
        except PathBoundaryError as exc:
            raise CommandError(str(exc)) from exc
        except LiveEvaluationError as exc:
            if exc.partial_result is not None:
                generated_at = datetime.now(timezone.utc).isoformat()
                try:
                    write_live_evaluation_reports(
                        exc.partial_result,
                        output_dir=output_dir,
                        generated_at=generated_at,
                    )
                except Exception as write_exc:
                    raise CommandError("partial_report_write_failure") from write_exc
            if exc.category == "raw_evidence_write_failure":
                cause = exc.__cause__ if exc.__cause__ is not None else exc
                raise CommandError("raw_evidence_write_failure") from cause
            raise CommandError(str(exc)) from exc
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(
                f"Live evaluation failed: {exc.__class__.__name__}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Phase 2C live evaluation complete: "
                f"overall_result={run.overall_result}; "
                f"calls_made={run.calls_made}; "
                f"actual_spend_usd={run.actual_spend_usd}"
            )
        )
        self.stdout.write(f"results={results_path}")
        self.stdout.write(f"summary={summary_path}")
