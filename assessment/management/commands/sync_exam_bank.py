import json
import hashlib
import tempfile
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assessment.services.bank_importer import BankValidationError, WorkbookBankImporter
from assessment.services.bank_sync import BankSyncService
from assessment.services.configuration_sync import MasterConfigurationSync
from assessment.models import ExamAttempt, ExamSession, GeneratedExam


class Command(BaseCommand):
    help = "Validate or synchronize the canonical assessment question bank"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true", help="Validate and report without database writes")
        mode.add_argument("--apply", action="store_true", help="Apply a previously validated source atomically")
        parser.add_argument("--source", help="Local XLSX path or HTTPS XLSX URL")
        parser.add_argument("--question-id", help="Restrict report to one QUESTION_ID (apply is prohibited)")
        parser.add_argument(
            "--initial-load", action="store_true",
            help="Require an empty runtime after reset before the canonical first apply",
        )

    def handle(self, *args, **options):
        if options["apply"] and options.get("question_id"):
            raise CommandError("--question-id is only supported with --dry-run")
        source = options.get("source") or getattr(settings, "QUESTION_BANK_SOURCE", "")
        if not source:
            file_id = getattr(settings, "QUESTION_BANK_FILE_ID", "") or (
                "1kyaIfu7NSA4PQ_b6UXb8rRqJYLCdsUNF3AA8_Cf1BbQ"
            )
            source = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
        if options["apply"] and not getattr(settings, "QUESTION_BANK_SYNC_ENABLED", False):
            raise CommandError("Apply is disabled; set QUESTION_BANK_SYNC_ENABLED=true")
        if options["initial_load"] and not options["apply"]:
            raise CommandError("--initial-load must be used together with --apply")
        if options["initial_load"]:
            runtime = {
                "ExamSession": ExamSession.objects.count(),
                "GeneratedExam": GeneratedExam.objects.count(),
                "ExamAttempt": ExamAttempt.objects.count(),
            }
            if any(runtime.values()):
                detail = ", ".join(f"{name}={count}" for name, count in runtime.items())
                raise CommandError(
                    "Initial bank load refused because legacy runtime data remains: "
                    f"{detail}. Run reset_assessment_for_bank_v2 --dry-run, then --apply."
                )

        temporary_path = None
        try:
            path = source
            if source.startswith(("https://", "http://")):
                if not source.startswith("https://"):
                    raise CommandError("Only HTTPS remote bank sources are allowed")
                response = requests.get(source, timeout=(10, 120), allow_redirects=True)
                response.raise_for_status()
                if len(response.content) > 50 * 1024 * 1024:
                    raise CommandError("Question-bank file exceeds 50 MiB")
                handle = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
                handle.write(response.content)
                handle.close()
                temporary_path = handle.name
                path = temporary_path
            elif Path(source).suffix.lower() != ".xlsx":
                raise CommandError("Question-bank source must be an .xlsx file")

            if not source.startswith(("https://", "http://")) and Path(source).name == (
                "INDEX_NGAN_HANG_DE_TIN_HOC_TOT_NGHIEP_MASTER.xlsx"
            ):
                file_id = getattr(settings, "QUESTION_BANK_FILE_ID", "") or (
                    "1kyaIfu7NSA4PQ_b6UXb8rRqJYLCdsUNF3AA8_Cf1BbQ"
                )
                remote = requests.get(
                    f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx",
                    timeout=(10, 120), allow_redirects=True,
                )
                remote.raise_for_status()
                local_hash = hashlib.sha256(Path(source).read_bytes()).hexdigest()
                remote_hash = hashlib.sha256(remote.content).hexdigest()
                if local_hash != remote_hash:
                    raise CommandError(
                        "STALE_BANK_SNAPSHOT: local canonical XLSX hash differs from live Google master; "
                        "sync using QUESTION_BANK_FILE_ID/HTTPS export."
                    )

            parsed = WorkbookBankImporter().parse(path)
            if options.get("question_id"):
                parsed.questions = [q for q in parsed.questions if q["question_id"] == options["question_id"]]
                parsed.errors = [e for e in parsed.errors if e.get("question_id") == options["question_id"]]
            report = BankSyncService().preview(parsed)
            report["configuration"] = MasterConfigurationSync().preview(parsed)
            report.update({
                "source_sha256": parsed.source_sha256,
                "mode": "APPLY_VALIDATION" if options["apply"] else "DRY_RUN",
            })
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, default=str))
            if parsed.has_fatal_errors:
                if options["apply"]:
                    self.stdout.write(json.dumps({
                        "mode": "APPLY_FAILED", "error": "Validation failed",
                        "source_sha256": parsed.source_sha256,
                    }, ensure_ascii=False, indent=2))
                raise CommandError("Validation failed; no changes were applied")
            if options["apply"]:
                try:
                    with transaction.atomic():
                        log = BankSyncService().apply(parsed, source_label=source)
                        configuration = MasterConfigurationSync().apply(parsed)
                except Exception as exc:
                    self.stdout.write(json.dumps({
                        "mode": "APPLY_FAILED", "error": str(exc),
                        "source_sha256": parsed.source_sha256,
                    }, ensure_ascii=False, indent=2))
                    raise CommandError("Apply failed; transaction rolled back") from exc
                self.stdout.write(json.dumps({
                    "mode": "APPLY_SUCCESS", "sync_log_id": log.pk,
                    "configuration_applied": configuration,
                    "source_sha256": parsed.source_sha256,
                }, ensure_ascii=False, indent=2, default=str))
            else:
                self.stdout.write(self.style.SUCCESS("Dry-run completed; database unchanged"))
        except (BankValidationError, requests.RequestException, OSError) as exc:
            raise CommandError(str(exc)) from exc
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)
