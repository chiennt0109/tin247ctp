from django.core.management.base import BaseCommand

from learning_analytics.scripts.import_skills import run


class Command(BaseCommand):
    help = "Import skill tree dataset from learning_analytics/data/skills.json"

    def handle(self, *args, **options):
        count = run()
        self.stdout.write(self.style.SUCCESS(f"Imported/updated {count} skills"))
