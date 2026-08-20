from collections import Counter
from decimal import Decimal

from assessment.models import BankQuestion
from assessment.services.blueprint_feasibility import solve_slot_assignment
from assessment.services.eligibility import graduation_eligible


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
            raw_candidates = list(self.candidates_for_slot(slot))
            candidates = raw_candidates
            excluded_by_previous_slots = 0
            candidate_count = len(candidates)
            # Empty family IDs represent unrelated questions and must each count
            # as a distinct selectable family.
            named_family_count = len({q.duplicate_family_id for q in candidates if q.duplicate_family_id})
            unnamed_count = sum(not q.duplicate_family_id for q in candidates)
            distinct_capacity = named_family_count + unnamed_count
            status = self._capacity_status(candidate_count, distinct_capacity, slot.quantity)
            availability.append({
                "slot_id": slot.pk, "required": slot.quantity, "candidates": candidate_count,
                "distinct_family_capacity": distinct_capacity, "status": status,
                "filters": self.explain_slot(slot),
                "excluded_by_previous_slots": excluded_by_previous_slots,
            })
            if candidate_count < slot.quantity:
                errors.append({"code": "INSUFFICIENT_CANDIDATES", "slot_id": slot.pk})
            elif distinct_capacity < slot.quantity:
                errors.append({"code": "INSUFFICIENT_DISTINCT_FAMILIES", "slot_id": slot.pk})
            elif candidate_count <= slot.quantity * 2:
                warnings.append({"code": "LOW_CANDIDATE_MARGIN", "slot_id": slot.pk})
            if (scoring_version is not None and slot.question_type not in scoring_types
                    and slot.question_type not in {"ESSAY", "PRACTICAL"}):
                errors.append({
                    "code": "MISSING_SCORING_RULE", "slot_id": slot.pk,
                    "question_type": slot.question_type,
                })

        assignment = solve_slot_assignment(slot_list, self.candidates_for_slot, seed="feasibility")
        if assignment is None:
            errors.append({"code": "NO_GLOBAL_DISTINCT_ASSIGNMENT"})

        report = {
            "valid": not errors, "question_total": question_total, "score_total": str(score_total),
            "errors": errors, "warnings": warnings, "availability": availability,
            "error_counts": dict(Counter(error["code"] for error in errors)),
        }
        return report

    @staticmethod
    def _candidate_queryset(slot):
        queryset = BankQuestion.objects.filter(
            is_available=True, current_revision__isnull=False, question_type=slot.question_type,
        )
        # A ready-for-X workflow state is the authoritative gate.  Physical
        # STATUS is deliberately not used as a substitute for this condition.
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

    @classmethod
    def candidates_for_slot(cls, slot):
        """Return the strict, deterministic DB-backed pool for a logical slot.

        ``required_tags`` is deliberately evaluated as structured metadata rather
        than text searching.  It supports either ``["TAG"]`` (membership in the
        question's ``tags`` metadata) or ``{"NLS_PRIMARY": "..."}`` style gates.
        This keeps NLS/AI separate from the subject competency field.
        """
        questions = cls._candidate_queryset(slot).order_by("source_question_id")
        return [question for question in questions if cls._metadata_matches(slot, question)
                and (not slot.requires_graduation_eligibility or graduation_eligible(question))]

    @staticmethod
    def _metadata_matches(slot, question):
        metadata = question.source_metadata or {}
        required = slot.required_tags or []
        excluded = slot.excluded_tags or []
        tags = set(metadata.get("tags") or metadata.get("TAGS") or [])
        if isinstance(required, dict):
            if any(metadata.get(key) != value for key, value in required.items()):
                return False
        elif any(tag not in tags for tag in required):
            return False
        if isinstance(excluded, dict):
            if any(metadata.get(key) == value for key, value in excluded.items()):
                return False
        elif any(tag in tags for tag in excluded):
            return False
        return True

    @classmethod
    def explain_slot(cls, slot):
        """Return progressive inventory counts so operators can see each exclusion."""
        queryset = BankQuestion.objects.filter(is_available=True, current_revision__isnull=False)
        stages = []

        def apply(label, **filters):
            nonlocal queryset
            before = queryset.count()
            queryset = queryset.filter(**filters)
            after = queryset.count()
            stages.append({"condition": label, "before": before, "after": after, "excluded": before - after})

        apply("question_type", question_type=slot.question_type)
        if slot.curriculum_id:
            apply("topic", curriculum_id=slot.curriculum_id)
        if slot.outcome_id:
            apply("YCCD", outcome_id=slot.outcome_id)
        if slot.cognitive_level:
            apply("cognitive_level", cognitive_level=slot.cognitive_level)
        if slot.difficulty is not None:
            apply("difficulty", difficulty=slot.difficulty)
        if slot.competency:
            apply("competency", competency=slot.competency)
        if slot.requires_graduation_eligibility:
            apply("eligibility", process_status="READY_FOR_GRADUATION")
        elif slot.required_process_status:
            apply("eligibility", process_status=slot.required_process_status)
        return stages

    @classmethod
    def format_failure(cls, report):
        lines = []
        availability = {row["slot_id"]: row for row in report.get("availability", [])}
        for error in report.get("errors", []):
            slot_id = error.get("slot_id")
            row = availability.get(slot_id)
            if not row:
                lines.append(error["code"])
                continue
            filters = ", ".join(
                f"{stage['condition']}: loại {stage['excluded']} (còn {stage['after']})"
                for stage in row["filters"]
            )
            if row.get("excluded_by_previous_slots"):
                filters += f", slot trước: loại {row['excluded_by_previous_slots']}"
            lines.append(
                f"Slot {slot_id}: cần {row['required']} / có {row['candidates']} "
                f"(sức chứa họ câu {row['distinct_family_capacity']}); {filters}"
            )
        return " | ".join(lines)

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
