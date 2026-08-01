import json

from django.core.management.base import BaseCommand

from assessment.services.demo_cleanup import AssessmentDemoCleanup


class Command(BaseCommand):
    help = "Inspect or remove only the two obsolete assessment demo sessions"

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        cleanup = AssessmentDemoCleanup()
        if options["dry_run"]:
            self.stdout.write(json.dumps(cleanup.inspect().as_dict(), indent=2))
            return
        before, after = cleanup.apply()
        self.stdout.write(json.dumps({"before": before.as_dict(), "after": after.as_dict()}, indent=2))
        if after.sessions:
            self.stderr.write(self.style.ERROR("Demo assessment sessions remain"))
        else:
            self.stdout.write(self.style.SUCCESS("The two obsolete demo sessions are absent"))
