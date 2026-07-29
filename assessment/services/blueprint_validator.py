from collections import Counter
from decimal import Decimal

from assessment.models import BankQuestion


class BlueprintValidator:
    """Validate totals, scoring coverage and live inventory for one version."""

    def validate(self, version, *, scoring_version=None):
        slots = list(
            version.sections.prefetch_related("slots__curriculum", "slots__outcome")
            .all()
        )
        slot_list = [slot for section in slots for slot in section.slots.all()]
        errors, warnings, availability = [], [], []
        question_total = sum(slot.quantity for slot in slot_list)
        score_total = sum((slot.score_per_item * slot.quantity for slot in slot_list), Decimal("0"))

        if question_total != version.expected_question_count:
            errors.append({
                "code": "QUESTION_TOTAL_MISMATCH", "expected": version.expected_question_count,
                "actual": question_total,
            })
        if score_total != version.expected_total_score:
            errors.append({
                "code": "SCORE_TOTAL_MISMATCH", "expected": str(version.expected_total_score),
                "actual": str(score_total),
            })

        scoring_types = set()
        if scoring_version is not None:
            scoring_types = set(scoring_version.rules.values_list("question_type", flat=True))

        for slot in slot_list:
            candidates = self._candidate_queryset(slot)
            candidate_count = candidates.count()
            # Empty family IDs represent unrelated questions and must each count
            # as a distinct selectable family.
            named_family_count = candidates.exclude(duplicate_family_id="").values(
                "duplicate_family_id"
            ).distinct().count()
            unnamed_count = candidates.filter(duplicate_family_id="").count()
            distinct_capacity = named_family_count + unnamed_count
            status = self._capacity_status(candidate_count, distinct_capacity, slot.quantity)
            availability.append({
                "slot_id": slot.pk, "required": slot.quantity, "candidates": candidate_count,
                "distinct_family_capacity": distinct_capacity, "status": status,
            })
            if candidate_count < slot.quantity:
                errors.append({"code": "INSUFFICIENT_CANDIDATES", "slot_id": slot.pk})
            elif distinct_capacity < slot.quantity:
                errors.append({"code": "INSUFFICIENT_DISTINCT_FAMILIES", "slot_id": slot.pk})
            elif candidate_count <= slot.quantity * 2:
                warnings.append({"code": "LOW_CANDIDATE_MARGIN", "slot_id": slot.pk})
            if scoring_version is not None and slot.question_type not in scoring_types:
                errors.append({
                    "code": "MISSING_SCORING_RULE", "slot_id": slot.pk,
                    "question_type": slot.question_type,
                })

        report = {
            "valid": not errors, "question_total": question_total, "score_total": str(score_total),
            "errors": errors, "warnings": warnings, "availability": availability,
            "error_counts": dict(Counter(error["code"] for error in errors)),
        }
        return report

    @staticmethod
    def _candidate_queryset(slot):
        queryset = BankQuestion.objects.filter(
            is_available=True, question_type=slot.question_type,
        )
        if slot.curriculum_id:
            queryset = queryset.filter(curriculum_id=slot.curriculum_id)
        if slot.outcome_id:
            queryset = queryset.filter(outcome_id=slot.outcome_id)
        if slot.cognitive_level:
            queryset = queryset.filter(cognitive_level=slot.cognitive_level)
        if slot.difficulty is not None:
            queryset = queryset.filter(difficulty=slot.difficulty)
        if slot.competency:
            queryset = queryset.filter(competency=slot.competency)
        if slot.requires_graduation_eligibility:
            queryset = queryset.filter(process_status="READY_FOR_GRADUATION")
        elif slot.required_process_status:
            queryset = queryset.filter(process_status=slot.required_process_status)
        return queryset

    @staticmethod
    def _capacity_status(candidates, distinct_capacity, required):
        usable = min(candidates, distinct_capacity)
        if usable == 0:
            return "NONE"
        if usable < required:
            return "INSUFFICIENT"
        if usable <= required * 2:
            return "TIGHT"
        return "SUFFICIENT"
