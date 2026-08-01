import json

from django.core.management.base import BaseCommand

from assessment.services.legacy_cleanup import AssessmentLegacyCleanup


class Command(BaseCommand):
    help = "Inspect or atomically remove assessment data left by the old assignment/preview flow"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        cleanup = AssessmentLegacyCleanup()
        if options["dry_run"]:
            self.stdout.write(json.dumps(cleanup.inspect().as_dict(), indent=2))
            return
        before, after = cleanup.apply()
        self.stdout.write(json.dumps({"before": before.as_dict(), "after": after.as_dict()}, indent=2))
        if any(after.as_dict().values()):
            self.stderr.write(self.style.ERROR("Assessment legacy cleanup did not reach zero state"))
        else:
            self.stdout.write(self.style.SUCCESS("Assessment legacy cleanup reached zero state"))
