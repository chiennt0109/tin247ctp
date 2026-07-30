import json
import tempfile
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from assessment.services.bank_importer import BankValidationError, WorkbookBankImporter
from assessment.services.bank_sync import BankSyncService


class Command(BaseCommand):
    help = "Validate or synchronize the canonical assessment question bank"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true", help="Validate and report without database writes")
        mode.add_argument("--apply", action="store_true", help="Apply a previously validated source atomically")
        parser.add_argument("--source", help="Local XLSX path or HTTPS XLSX URL")
        parser.add_argument("--question-id", help="Restrict report to one QUESTION_ID (apply is prohibited)")

    def handle(self, *args, **options):
        if options["apply"] and options.get("question_id"):
            raise CommandError("--question-id is only supported with --dry-run")
        source = options.get("source") or getattr(settings, "QUESTION_BANK_SOURCE", "")
        if not source:
            file_id = getattr(settings, "QUESTION_BANK_FILE_ID", "")
            if file_id:
                source = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
        if not source:
            raise CommandError("Set --source, QUESTION_BANK_SOURCE, or QUESTION_BANK_FILE_ID")
        if options["apply"] and not getattr(settings, "QUESTION_BANK_SYNC_ENABLED", False):
            raise CommandError("Apply is disabled; set QUESTION_BANK_SYNC_ENABLED=true")

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

            parsed = WorkbookBankImporter().parse(path)
            if options.get("question_id"):
                parsed.questions = [q for q in parsed.questions if q["question_id"] == options["question_id"]]
                parsed.errors = [e for e in parsed.errors if e.get("question_id") == options["question_id"]]
            report = BankSyncService().preview(parsed)
            report.update({"source_sha256": parsed.source_sha256, "mode": "APPLY" if options["apply"] else "DRY_RUN"})
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, default=str))
            if parsed.has_fatal_errors:
                raise CommandError("Validation failed; no changes were applied")
            if options["apply"]:
                log = BankSyncService().apply(parsed, source_label=source)
                self.stdout.write(self.style.SUCCESS(f"Applied atomically; sync log #{log.pk}"))
            else:
                self.stdout.write(self.style.SUCCESS("Dry-run completed; database unchanged"))
        except (BankValidationError, requests.RequestException, OSError) as exc:
            raise CommandError(str(exc)) from exc
        finally:
            if temporary_path:
                Path(temporary_path).unlink(missing_ok=True)
