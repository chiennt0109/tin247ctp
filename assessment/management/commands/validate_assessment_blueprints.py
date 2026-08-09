import json

from django.core.management.base import BaseCommand, CommandError

from assessment.models import BlueprintVersion
from assessment.services.blueprint_validator import BlueprintValidator


class Command(BaseCommand):
    help = "Validate blueprint structure and distinct-family question capacity (read-only)."

    def add_arguments(self, parser):
        parser.add_argument("--blueprint-id")
        parser.add_argument("--grade", type=int)
        parser.add_argument("--mode", choices=("periodic", "graduation"))
        parser.add_argument("--show-pool", action="store_true")

    def handle(self, *args, **options):
        versions = BlueprintVersion.objects.select_related("blueprint").order_by(
            "blueprint__source_blueprint_id", "-version"
        )
        if options["blueprint_id"]:
            versions = versions.filter(blueprint__source_blueprint_id=options["blueprint_id"])
        if options["grade"]:
            versions = versions.filter(blueprint__grade=options["grade"])
        if options["mode"]:
            versions = versions.filter(blueprint__exam_type=options["mode"].upper())
        if not versions.exists():
            raise CommandError("No blueprint version matches the requested filters")
        validator = BlueprintValidator()
        for version in versions:
            report = validator.validate(version)
            payload = {
                "blueprint_id": version.blueprint.source_blueprint_id or version.blueprint_id,
                "version": version.version,
                "status": version.blueprint.status,
                "grade": version.blueprint.grade,
                "mode": version.blueprint.exam_type,
                "duration_minutes": version.duration_minutes,
                "question_total": report["question_total"],
                "score_total": report["score_total"],
                "valid": report["valid"],
                "errors": report["errors"],
            }
            if options["show_pool"]:
                payload["pool"] = report["availability"]
            self.stdout.write(json.dumps(payload, ensure_ascii=False, default=str))

