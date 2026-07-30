from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from assessment.services.demo_seed import AssessmentDemoSeeder, resolve_user


class Command(BaseCommand):
    help = "Create idempotent [DEMO] assessment blueprints, scoring, sessions and generated exams"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")
        mode.add_argument("--reset", action="store_true", help="Delete demo-only data, then recreate it")
        parser.add_argument("--source", help="Canonical master XLSX path")
        parser.add_argument("--student", help="Existing student username to assign")
        parser.add_argument("--teacher", help="Existing teacher/admin username for audit ownership")
        parser.add_argument("--with-sample-attempts", action="store_true")

    def handle(self, *args, **options):
        if options["with_sample_attempts"]:
            raise CommandError("Sample attempts are unavailable until the Phase 5 attempt/grading service exists")
        source = options.get("source") or getattr(settings, "QUESTION_BANK_SOURCE", "")
        if not source:
            source = settings.BASE_DIR / "assessment/data/INDEX_NGAN_HANG_DE_TIN_HOC_TOT_NGHIEP_MASTER.xlsx"
        source = Path(source)
        if not source.exists():
            raise CommandError(f"Canonical workbook not found: {source}")
        try:
            student = resolve_user(options.get("student"))
            teacher = resolve_user(options.get("teacher"))
            seeder = AssessmentDemoSeeder(source)
            if options["dry_run"]:
                report = seeder.plan()
            else:
                with transaction.atomic():
                    reset_counts = seeder.reset() if options["reset"] else {}
                    report = seeder.apply(student=student, teacher=teacher)
                    report.reset_counts = reset_counts
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        self._print_report(report)

    def _print_report(self, report):
        self.stdout.write(self.style.MIGRATE_HEADING("ASSESSMENT DEMO SEED"))
        self.stdout.write("\nQuestion bank:")
        self.stdout.write(f"- Available questions: {report.bank.get('available', 0)}")
        self.stdout.write(f"- Periodic eligible: {report.bank.get('periodic', 0)}")
        self.stdout.write(f"- Graduation eligible: {report.bank.get('graduation', 0)}")
        self.stdout.write("\nBlueprints:")
        self.stdout.write(f"- Created: {report.blueprints_created}")
        self.stdout.write(f"- Existing: {report.blueprints_existing}")
        self.stdout.write("\nScoring schemes:")
        self.stdout.write(f"- Created: {report.schemes_created}")
        self.stdout.write(f"- Existing: {report.schemes_existing}")
        self.stdout.write("\nExam sessions:")
        self.stdout.write(f"- Created: {report.sessions_created}")
        self.stdout.write(f"- Existing: {report.sessions_existing}")
        if report.slot_reports:
            self.stdout.write("\nBlueprint slots:")
            for index, slot in enumerate(report.slot_reports, 1):
                self.stdout.write(
                    f"- {slot['blueprint']} / Slot {index}: topic={slot.get('topic', '-')}, "
                    f"outcome={slot.get('outcome', '-')}, level={slot.get('level', '-')}, "
                    f"type={slot.get('question_type', '-')}, required={slot['required']}, "
                    f"available={slot['candidates']}, status={slot['status']}"
                )
        self.stdout.write("\nGenerated exams:")
        for exam in report.generated:
            self.stdout.write(
                f"- {exam['session']} / {exam['code']}: questions={exam['questions']}, "
                f"score={exam['score']}, blueprint_valid={'YES' if exam['blueprint_valid'] else 'NO'}, "
                f"hash={exam['hash']}"
            )
        if not report.generated:
            self.stdout.write("- None")
        self.stdout.write("\nParticipants:")
        self.stdout.write("\n".join(f"- {item}" for item in report.participants) or "- None")
        if report.reset_counts:
            self.stdout.write("\nReset counts:")
            for key, value in report.reset_counts.items():
                self.stdout.write(f"- {key}: {value}")
        self.stdout.write("\nWarnings:")
        self.stdout.write("\n".join(f"- {warning}" for warning in report.warnings) or "- None")
        self.stdout.write("\nURLs:")
        self.stdout.write("- Admin: /admin/assessment/")
        self.stdout.write("- Student exam list: /assessment/exams/")
