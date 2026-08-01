from pathlib import Path

from django.core.management.base import BaseCommand

from assessment.tests import REMOVED_TEST_MODULES


class Command(BaseCommand):
    help = "Report obsolete assessment source files left untracked on a deployment"

    def handle(self, *args, **options):
        tests_dir = Path(__file__).resolve().parents[2] / "tests"
        stale = [tests_dir / f"{name}.py" for name in sorted(REMOVED_TEST_MODULES)]
        stale = [path for path in stale if path.exists()]
        if stale:
            self.stdout.write(self.style.WARNING("Obsolete untracked assessment tests:"))
            for path in stale:
                self.stdout.write(f"- {path}")
            self.stdout.write("Remove these files; they are not part of the current architecture.")
            return
        self.stdout.write(self.style.SUCCESS("Assessment source tree contains no obsolete test modules."))
