"""Controlled SkillEntry ownership backfill for Sprint 110A Phase 1."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.skill_ledger.models import SkillEntry

CONFIRMATION_TOKEN = "I_CONFIRM_SKILLENTRY_OWNERSHIP_BACKFILL"
User = get_user_model()


class Command(BaseCommand):
    help = (
        "Assign an explicit owner to unowned SkillEntry rows. "
        "Dry-run by default. Writes only when --apply is supplied."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            required=True,
            help="Explicit owner user primary key. No fallback selection is allowed.",
        )
        parser.add_argument(
            "--expected-unowned-count",
            type=int,
            required=True,
            help="Exact expected count of SkillEntry rows with user IS NULL.",
        )
        parser.add_argument(
            "--confirm",
            required=True,
            help=f'Must equal "{CONFIRMATION_TOKEN}".',
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report without writing (default when --apply is absent).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply ownership updates inside a transaction.",
        )

    def handle(self, *args, **options):
        apply_mode = bool(options["apply"])
        dry_run_mode = bool(options["dry_run"])
        if apply_mode and dry_run_mode:
            raise CommandError(
                "Provide either --dry-run or --apply, not both."
            )
        mode = "apply" if apply_mode else "dry-run"

        user_id = options["user_id"]
        expected_unowned_count = options["expected_unowned_count"]
        confirm = options["confirm"]

        if expected_unowned_count < 0:
            raise CommandError("expected-unowned-count must be non-negative.")

        if confirm != CONFIRMATION_TOKEN:
            raise CommandError("Confirmation token rejected.")

        try:
            owner = User.objects.get(pk=user_id)
        except User.DoesNotExist as exc:
            raise CommandError(f"User id={user_id} does not exist.") from exc

        if not owner.is_active:
            raise CommandError(f"User id={user_id} is inactive.")

        unowned_qs = SkillEntry.objects.filter(user__isnull=True)
        observed_unowned_count = unowned_qs.count()
        if observed_unowned_count != expected_unowned_count:
            raise CommandError(
                "Unowned SkillEntry count mismatch: "
                f"expected={expected_unowned_count}; "
                f"observed={observed_unowned_count}."
            )

        eligible_count = observed_unowned_count
        rows_updated = 0

        if apply_mode and eligible_count > 0:
            with transaction.atomic():
                rows_updated = SkillEntry.objects.filter(user__isnull=True).update(
                    user_id=owner.pk
                )
                remaining = SkillEntry.objects.filter(user__isnull=True).count()
                if remaining != 0:
                    raise CommandError(
                        "Ownership backfill failed closed: "
                        f"unowned rows remain after apply ({remaining})."
                    )
                if rows_updated != expected_unowned_count:
                    raise CommandError(
                        "Ownership backfill failed closed: "
                        f"updated={rows_updated}; "
                        f"expected={expected_unowned_count}."
                    )
        elif apply_mode:
            rows_updated = 0

        result = "success"
        self.stdout.write(f"mode={mode}")
        self.stdout.write(f"owner_user_id={owner.pk}")
        self.stdout.write(f"expected_unowned_count={expected_unowned_count}")
        self.stdout.write(f"observed_unowned_count={observed_unowned_count}")
        self.stdout.write(f"rows_eligible={eligible_count}")
        self.stdout.write(f"rows_updated={rows_updated}")
        self.stdout.write(f"result={result}")
