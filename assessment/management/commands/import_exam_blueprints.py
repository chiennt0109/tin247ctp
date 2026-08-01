import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assessment.services.bank_importer import BankValidationError, WorkbookBankImporter
from assessment.services.configuration_sync import MasterConfigurationSync


class Command(BaseCommand):
    help = "Import ExamBlueprint/BlueprintSlot rows from the canonical master XLSX"

    def add_arguments(self, parser):
        parser.add_argument("source", help="Path to INDEX_NGAN_HANG_DE_TIN_HOC_TOT_NGHIEP_MASTER.xlsx")
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        source = Path(options["source"])
        if source.suffix.lower() != ".xlsx" or not source.is_file():
            raise CommandError("Source must be an existing .xlsx workbook")
        try:
            parsed = WorkbookBankImporter().parse(source)
        except (BankValidationError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        service = MasterConfigurationSync()
        report = service.preview(parsed)
        if parsed.has_fatal_errors:
            raise CommandError("Workbook validation failed; no blueprint was imported")
        if options["apply"]:
            with transaction.atomic():
                report = service.apply(parsed)
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2, default=str))
        self.stdout.write(self.style.SUCCESS("Applied atomically" if options["apply"] else "Dry-run; database unchanged"))
