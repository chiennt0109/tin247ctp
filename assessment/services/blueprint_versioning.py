from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from assessment.models import (
    AssessmentAuditLog, BlueprintSection, BlueprintSlot, BlueprintVersion, ExamBlueprint,
)
from assessment.services.blueprint_validator import BlueprintValidator


@transaction.atomic
def clone_blueprint_version(source, *, actor=None):
    next_version = (source.blueprint.versions.aggregate(value=Max("version"))["value"] or 0) + 1
    clone = BlueprintVersion.objects.create(
        blueprint=source.blueprint, version=next_version,
        duration_minutes=source.duration_minutes,
        expected_question_count=source.expected_question_count,
        expected_total_score=source.expected_total_score,
        source_blueprint_id=source.source_blueprint_id,
        source_snapshot=source.source_snapshot,
        created_by=actor,
    )
    for section in source.sections.prefetch_related("slots").all():
        new_section = BlueprintSection.objects.create(
            version=clone, code=section.code, name=section.name,
            order=section.order, instructions=section.instructions,
        )
        BlueprintSlot.objects.bulk_create([
            BlueprintSlot(
                section=new_section, order=slot.order, curriculum=slot.curriculum,
                outcome=slot.outcome, question_type=slot.question_type,
                cognitive_level=slot.cognitive_level, difficulty=slot.difficulty,
                competency=slot.competency, quantity=slot.quantity,
                score_per_item=slot.score_per_item, required_tags=slot.required_tags,
                excluded_tags=slot.excluded_tags,
                requires_graduation_eligibility=slot.requires_graduation_eligibility,
                required_process_status=slot.required_process_status,
                allow_previously_used=slot.allow_previously_used,
                max_usage_count=slot.max_usage_count,
                reuse_cooldown_days=slot.reuse_cooldown_days,
                shortage_priority=slot.shortage_priority,
            ) for slot in section.slots.all()
        ])
    AssessmentAuditLog.objects.create(
        action="CLONE_BLUEPRINT_VERSION", actor=actor, object_type="BlueprintVersion",
        object_id=str(clone.pk), details={"source_version_id": source.pk},
    )
    return clone


@transaction.atomic
def lock_blueprint_version(version, *, scoring_version=None, approver=None):
    report = BlueprintValidator().validate(version, scoring_version=scoring_version)
    if not report["valid"]:
        raise ValueError("Cannot lock an invalid blueprint version")
    version.validation_report = report
    version.approved_by = approver
    version.approved_at = timezone.now()
    version.is_locked = True
    version.save(update_fields=("validation_report", "approved_by", "approved_at", "is_locked"))
    ExamBlueprint.objects.filter(pk=version.blueprint_id).update(
        total_questions=version.expected_question_count,
        total_score=version.expected_total_score,
        duration_minutes=version.duration_minutes,
        is_locked=True,
        is_ready=True,
    )
    AssessmentAuditLog.objects.create(
        action="LOCK_BLUEPRINT_VERSION", actor=approver, object_type="BlueprintVersion",
        object_id=str(version.pk), details={"validation_report": report},
    )
    return report
