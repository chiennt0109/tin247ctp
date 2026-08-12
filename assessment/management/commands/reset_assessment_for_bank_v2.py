"""Safely remove Assessment business/bank data before a canonical v2 sync."""

from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from assessment import models


# Child-first. Authentication, DMOJ data and global trial/abuse configuration
# are deliberately absent. Session-scoped grants disappear with their session.
PURGE_MODELS = (
    models.AttemptAnswer, models.GradingResult, models.ExamUsageRecord,
    models.ExamResourcePackage, models.ExamAttempt, models.GeneratedExamAsset,
    models.GeneratedExamQuestion, models.GeneratedExam, models.ExamAccessGrant,
    models.ExamSession, models.BlueprintSlot, models.BlueprintSection,
    models.BlueprintVersion, models.ExamBlueprintGroup, models.ExamBlueprint,
    models.ScoringRule, models.ScoringSchemeVersion, models.ScoringScheme,
    models.QuestionAsset, models.BankQuestionRevision, models.BankQuestion,
    models.CurriculumOutcome, models.CurriculumNode, models.BankSourceFile,
    models.QuestionSyncLog,
)


class Command(BaseCommand):
    help = "Backup PostgreSQL, then atomically reset Assessment for the canonical NLS/AI bank"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")
        parser.add_argument("--backup-dir", default="var/backups/assessment")

    @staticmethod
    def _table_exists(model):
        return model._meta.db_table in connection.introspection.table_names()

    def _counts(self):
        return [(model, model.objects.count() if self._table_exists(model) else None)
                for model in PURGE_MODELS]

    def _backup(self, directory):
        db = settings.DATABASES["default"]
        if "postgresql" not in db.get("ENGINE", ""):
            raise CommandError("--apply requires PostgreSQL; no purge was performed")
        directory = Path(directory).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / f"assessment-bank-v2-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.dump"
        command = ["pg_dump", "--format=custom", "--file", str(output)]
        for flag, key in (("--host", "HOST"), ("--port", "PORT"), ("--username", "USER")):
            if db.get(key):
                command.extend((flag, str(db[key])))
        command.append(str(db["NAME"]))
        env = os.environ.copy()
        if db.get("PASSWORD"):
            env["PGPASSWORD"] = str(db["PASSWORD"])
        result = subprocess.run(command, env=env, capture_output=True, text=True, check=False)
        if result.returncode or not output.is_file() or output.stat().st_size == 0:
            output.unlink(missing_ok=True)
            raise CommandError(f"PostgreSQL backup failed; no purge was performed: {result.stderr.strip()}")
        # pg_restore --list verifies that the custom archive is readable.
        verify = subprocess.run(["pg_restore", "--list", str(output)], capture_output=True, text=True, check=False)
        if verify.returncode:
            raise CommandError(f"Backup verification failed; no purge was performed: {verify.stderr.strip()}")
        self.stdout.write(self.style.SUCCESS(f"Verified PostgreSQL backup: {output}"))
        return output

    def handle(self, *args, **options):
        counts = self._counts()
        for model, count in counts:
            value = count if count is not None else "TABLE MISSING (skipped)"
            self.stdout.write(f"{model._meta.label}: {value}")
        if options["dry_run"]:
            self.stdout.write(self.style.SUCCESS("Dry-run only: no backup required and no rows deleted."))
            return
        backup = self._backup(options["backup_dir"])
        try:
            with transaction.atomic():
                # Break BankQuestion.current_revision -> BankQuestionRevision's
                # PROTECT cycle before deleting the bank child-first.
                if self._table_exists(models.BankQuestion):
                    models.BankQuestion.objects.update(current_revision=None)
                for model, count in counts:
                    if count is not None:
                        model.objects.all().delete()
        except Exception as exc:
            raise CommandError(f"Purge rolled back. Backup retained at {backup}: {exc}") from exc
        self.stdout.write(self.style.SUCCESS(f"Assessment reset complete. Backup retained at: {backup}"))
