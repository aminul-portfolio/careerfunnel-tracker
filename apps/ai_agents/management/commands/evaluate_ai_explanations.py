"""Management command for Phase 2B offline and structured-replay evaluation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.ai_agents.evaluation.cases import (
    CaseValidationError,
    load_case_set,
    load_replay_bundle,
)
from apps.ai_agents.evaluation.reporting import (
    PathBoundaryError,
    ensure_outside_repository,
    write_evaluation_reports,
)
from apps.ai_agents.evaluation.runner import (
    EvaluationRunnerError,
    run_evaluation,
)


class Command(BaseCommand):
    help = (
        "Run CareerFunnel P1 Phase 2B offline or structured-replay evaluation. "
        "Phase 2B is zero-network. Live provider execution is unsupported. "
        "Case sets, replay bundles and output directories must resolve outside "
        "the repository."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=("offline", "replay"),
            required=True,
            help="Evaluation mode. Only offline and replay are supported.",
        )
        parser.add_argument(
            "--case-set",
            required=True,
            help="Absolute path to an external case-set JSON file.",
        )
        parser.add_argument(
            "--output-dir",
            required=True,
            help="Absolute path to an external output directory.",
        )
        parser.add_argument(
            "--replay-bundle",
            default=None,
            help="Absolute path to an external replay bundle JSON file.",
        )

    def handle(self, *args, **options):
        mode = options["mode"]
        if mode == "live":
            raise CommandError("Live mode is unsupported in Phase 2B.")
        if mode not in {"offline", "replay"}:
            raise CommandError("Mode must be offline or replay.")

        replay_bundle_arg = options.get("replay_bundle")
        if mode == "replay" and not replay_bundle_arg:
            raise CommandError("Replay mode requires --replay-bundle.")
        if mode == "offline" and replay_bundle_arg:
            raise CommandError("Offline mode must not receive --replay-bundle.")

        try:
            case_set_path = ensure_outside_repository(
                Path(options["case_set"]),
                label="case_set",
            )
            output_dir = ensure_outside_repository(
                Path(options["output_dir"]),
                label="output_dir",
            )
            replay_path = None
            if replay_bundle_arg:
                replay_path = ensure_outside_repository(
                    Path(replay_bundle_arg),
                    label="replay_bundle",
                )
        except PathBoundaryError as exc:
            raise CommandError(str(exc)) from exc

        if not case_set_path.is_file():
            raise CommandError("Case-set path does not exist or is not a file.")
        if replay_path is not None and not replay_path.is_file():
            raise CommandError(
                "Replay-bundle path does not exist or is not a file."
            )

        try:
            case_set = load_case_set(case_set_path)
            replay_bundle = None
            if replay_path is not None:
                replay_bundle = load_replay_bundle(
                    replay_path,
                    expected_case_ids=frozenset(
                        case.case_id for case in case_set.cases
                    ),
                    expected_case_set_hash=case_set.case_set_hash,
                )
            run = run_evaluation(
                case_set,
                mode=mode,
                replay_bundle=replay_bundle,
            )
            generated_at = datetime.now(timezone.utc).isoformat()
            results_path, summary_path = write_evaluation_reports(
                run,
                output_dir=output_dir,
                generated_at=generated_at,
            )
        except PathBoundaryError as exc:
            raise CommandError(str(exc)) from exc
        except CaseValidationError as exc:
            raise CommandError(str(exc)) from exc
        except EvaluationRunnerError as exc:
            if exc.partial_result is not None:
                generated_at = datetime.now(timezone.utc).isoformat()
                try:
                    write_evaluation_reports(
                        exc.partial_result,
                        output_dir=output_dir,
                        generated_at=generated_at,
                    )
                except Exception:
                    pass
            raise CommandError(str(exc)) from exc
        except Exception as exc:
            raise CommandError(
                f"Evaluation failed: {exc.__class__.__name__}"
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                "Phase 2B evaluation complete: "
                f"overall_result={run.overall_result}; "
                f"case_count={run.case_count}; "
                f"pass={run.pass_count}; "
                f"fail={run.fail_count}; "
                f"review_required={run.review_required_count}"
            )
        )
        self.stdout.write(f"results={results_path}")
        self.stdout.write(f"summary={summary_path}")
