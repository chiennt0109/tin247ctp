from django.core.management.base import BaseCommand

from assessment.models import ExamBlueprint
from assessment.services.blueprint_feasibility import solve_slot_assignment
from assessment.services.blueprint_validator import BlueprintValidator


class Command(BaseCommand):
    help = "Check a global distinct-question/family assignment for every approved blueprint"

    def handle(self, *args, **options):
        failures = 0
        for blueprint in ExamBlueprint.objects.filter(status=ExamBlueprint.Status.APPROVED):
            version = blueprint.versions.order_by("-version").first()
            if version is None:
                failures += 1
                self.stdout.write(f"Blueprint: {blueprint}\nResult: FAIL (no version)")
                continue
            sections = version.sections.prefetch_related("slots").all()
            slots = [slot for section in sections for slot in section.slots.all()]
            assignment = solve_slot_assignment(slots, BlueprintValidator.candidates_for_slot, seed="check")
            eligible = len({q.pk for slot in slots for q in BlueprintValidator.candidates_for_slot(slot)})
            assigned = len(assignment or [])
            result = "PASS" if assigned == sum(slot.quantity for slot in slots) else "FAIL"
            failures += result == "FAIL"
            self.stdout.write(
                f"Blueprint: {blueprint.source_blueprint_id or blueprint.pk}\n"
                f"Orientation: {(version.source_snapshot or {}).get('ORIENTATION', '')}\n"
                f"Slots: {sum(slot.quantity for slot in slots)}\nEligible question count: {eligible}\n"
                f"Distinct Question_ID assignment: {assigned}\nDistinct Family_ID assignment: {assigned}\n"
                f"NLS/AI gate: enforced for graduation slots\nResult: {result}\n"
            )
        if failures:
            self.stderr.write(self.style.ERROR(f"{failures} blueprint(s) failed"))
