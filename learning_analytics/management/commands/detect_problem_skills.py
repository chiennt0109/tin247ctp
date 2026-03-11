from django.core.management.base import BaseCommand

from learning_analytics.skill_detector import detect_and_assign
from problems.models import Problem


class Command(BaseCommand):
    help = "Detect and attach skills for all existing problems using title/statement/tags"

    def add_arguments(self, parser):
        parser.add_argument("--refresh", action="store_true", help="Rebuild links for each problem before assigning")
        parser.add_argument("--min-score", type=int, default=2, help="Minimum confidence score for assignment")

    def handle(self, *args, **options):
        refresh = options["refresh"]
        min_score = options["min_score"]
        created_total = 0
        detected_count = 0

        for problem in Problem.objects.prefetch_related("tags").all():
            detected, created = detect_and_assign(problem, min_score=min_score, refresh=refresh)
            created_total += created
            if detected:
                detected_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Detected skills for {detected_count} problems, created {created_total} problem-skill links"
            )
        )
