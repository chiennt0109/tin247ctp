import random

from django.core.management.base import BaseCommand, CommandError

from assessment.models import BlueprintVersion
from assessment.services.blueprint_validator import BlueprintValidator


class Command(BaseCommand):
    help = "Preview seeded slot selection without creating exams, items, or attempts."

    def add_arguments(self, parser):
        parser.add_argument("--blueprint-id", required=True)
        parser.add_argument("--seed", required=True)

    def handle(self, *args, **options):
        version = BlueprintVersion.objects.filter(
            blueprint__source_blueprint_id=options["blueprint_id"]
        ).order_by("-version").first()
        if not version:
            raise CommandError("Blueprint not found")
        report = BlueprintValidator().validate(version)
        if not report["valid"]:
            raise CommandError(BlueprintValidator.format_failure(report))
        rng, used = random.Random(str(options["seed"])), set()
        for section in version.sections.prefetch_related("slots__curriculum", "slots__outcome"):
            for slot in section.slots.all():
                candidates = BlueprintValidator.candidates_for_slot(slot)
                rng.shuffle(candidates)
                chosen = []
                for question in candidates:
                    family = question.duplicate_family_id or f"QUESTION:{question.source_question_id}"
                    if family in used:
                        continue
                    used.add(family)
                    chosen.append(question)
                    if len(chosen) == slot.quantity:
                        break
                for question in chosen:
                    metadata = question.source_metadata or {}
                    self.stdout.write(" | ".join(map(str, (
                        slot.pk, question.source_question_id, question.question_type,
                        question.curriculum_id or "-", question.outcome_id or "-",
                        question.cognitive_level, question.difficulty,
                        question.duplicate_family_id or "-", metadata.get("NLS_PRIMARY", "-"),
                        slot.score_per_item,
                    ))))
