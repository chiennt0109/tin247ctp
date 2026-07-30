import json

from django.core.management.base import BaseCommand, CommandError

from assessment.services.phase4_cleanup import Phase4CleanupSchemaError, Phase4LegacyCleanup


class Command(BaseCommand):
    help = "Inspect or remove pre-generated Phase 4 assessment artifacts"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        cleanup = Phase4LegacyCleanup()
        if options["dry_run"]:
            self._print(cleanup.inspect(), "DRY-RUN")
            return
        try:
            before, after = cleanup.apply()
        except Phase4CleanupSchemaError as exc:
            raise CommandError(str(exc)) from exc
        self._print(before, "BEFORE APPLY")
        self._print(after, "AFTER APPLY")

    def _print(self, report, heading):
        data = report.as_dict()
        self.stdout.write(self.style.MIGRATE_HEADING(f"ASSESSMENT PHASE 4 CLEANUP — {heading}"))
        self.stdout.write(f"Schema state: {data['schema_state']}")
        if data["schema_state"] != "CURRENT":
            self.stdout.write(self.style.WARNING(
                "Pre-0007 inspection mode: counts are read-only; run migration 0007 before --apply."
            ))
        labels = (
            ("Legacy GeneratedExam", "legacy_generated_exams"),
            ("Legacy GeneratedExamQuestion", "legacy_generated_exam_questions"),
            ("Legacy exam assignments", "legacy_exam_assignments"),
            ("Legacy demo participants", "legacy_demo_participants"),
            ("Legacy preview exams", "legacy_preview_exams"),
            ("Orphan GeneratedExam", "orphan_generated_exams"),
            ("Orphan GeneratedExamQuestion", "orphan_generated_exam_questions"),
            ("Broken IN_PROGRESS attempts", "broken_attempts"),
            ("Obsolete demo sessions", "obsolete_demo_sessions"),
        )
        for label, key in labels:
            self.stdout.write(f"{label}: {data[key]}")
        self.stdout.write(f"Objects preserved: {json.dumps(data['preserved'], sort_keys=True)}")
