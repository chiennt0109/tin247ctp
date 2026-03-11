from django.core.management.base import BaseCommand

from learning_analytics.scripts.tag_problems_by_skill import run


class Command(BaseCommand):
    help = "Auto assign skills to problems by existing tags"

    def handle(self, *args, **options):
        linked = run()
        self.stdout.write(self.style.SUCCESS(f"Created {linked} problem-skill links"))
