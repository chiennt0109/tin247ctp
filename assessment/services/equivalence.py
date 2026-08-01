from collections import Counter
from decimal import Decimal

from django.db import transaction

from assessment.models import ExamBlueprint
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.session_configuration import resolve_locked_configuration
from django.core.exceptions import ValidationError


def _signature(version):
    slots = list(version.sections.prefetch_related("slots").all())
    slots = [slot for section in slots for slot in section.slots.all()]
    total = sum(slot.quantity for slot in slots)
    cognitive = Counter()
    difficulty = Counter()
    types = Counter()
    coverage = set()
    for slot in slots:
        types[slot.question_type] += slot.quantity
        cognitive[slot.cognitive_level or "-"] += slot.quantity
        difficulty[str(slot.difficulty or "-")] += slot.quantity
        coverage.add((slot.curriculum_id, slot.outcome_id))
    proportions = {key: Decimal(value) / total for key, value in cognitive.items()} if total else {}
    difficulty_profile = {
        key: Decimal(value) / total for key, value in difficulty.items()
    } if total else {}
    return {
        "types": types, "cognitive": proportions, "difficulty": difficulty_profile,
        "coverage": coverage,
    }


@transaction.atomic
def validate_equivalence_group(group):
    rows = []
    reference = None
    for blueprint in group.blueprints.order_by("name"):
        version = blueprint.versions.filter(is_locked=True).order_by("-version").first()
        errors, warnings = [], []
        report = None
        signature = None
        if version is None:
            errors.append("Chưa có phiên bản LOCKED")
        else:
            if blueprint.exam_type != group.exam_type:
                warnings.append("Khác loại kỳ thi")
            try:
                resolved_version, scoring_version = resolve_locked_configuration(blueprint)
            except ValidationError as exc:
                scoring_version = None
                errors.extend(exc.messages)
            else:
                version = resolved_version
            report = BlueprintValidator().validate(version, scoring_version=scoring_version)
            signature = _signature(version)
            if not report["valid"]:
                errors.append(BlueprintValidator.format_failure(report) or "Ma trận không hợp lệ")
            if reference is None and report["valid"]:
                reference = (version, signature)
            elif reference:
                reference_version, reference_signature = reference
                if version.expected_question_count != reference_version.expected_question_count:
                    warnings.append("Khác tổng số câu")
                if version.expected_total_score != reference_version.expected_total_score:
                    warnings.append("Khác tổng điểm")
                if abs(version.duration_minutes - reference_version.duration_minutes) > group.duration_tolerance_minutes:
                    warnings.append("Khác thời lượng vượt ngưỡng")
                if signature["types"] != reference_signature["types"]:
                    warnings.append("Khác cơ cấu loại câu")
                levels = set(signature["cognitive"]) | set(reference_signature["cognitive"])
                if any(abs(signature["cognitive"].get(level, 0) - reference_signature["cognitive"].get(level, 0)) > group.cognitive_tolerance for level in levels):
                    warnings.append("Tỷ lệ mức độ nhận thức vượt ngưỡng")
        ready = group.is_active and version is not None and not errors
        if version:
            ExamBlueprint.objects.filter(pk=blueprint.pk).update(
                total_questions=version.expected_question_count,
                total_score=version.expected_total_score,
                duration_minutes=version.duration_minutes,
                is_locked=True, is_ready=ready,
                difficulty_profile={
                    "difficulty": {key: str(value) for key, value in (signature or {}).get("difficulty", {}).items()},
                    "cognitive": {key: str(value) for key, value in (signature or {}).get("cognitive", {}).items()},
                },
            )
        else:
            ExamBlueprint.objects.filter(pk=blueprint.pk).update(is_locked=False, is_ready=False)
        rows.append({
            "blueprint": blueprint, "version": version, "ready": ready,
            "errors": errors, "warnings": warnings,
            "coverage": len((signature or {}).get("coverage", set())),
            "difficulty_profile": (signature or {}).get("cognitive", {}),
            "availability": (report or {}).get("availability", []),
        })
    return rows
