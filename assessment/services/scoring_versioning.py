from copy import deepcopy

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max

from assessment.models import AssessmentAuditLog, ScoringRule, ScoringSchemeVersion


def validate_scoring_version(version, *, blueprint_version=None):
    rules = list(version.rules.order_by("order", "pk"))
    errors = []
    if version.total_score <= 0:
        errors.append("Tổng điểm phải lớn hơn 0.")
    if not rules:
        errors.append("Phiên bản phải có ít nhất một quy tắc chấm.")
    for rule in rules:
        try:
            rule.full_clean()
        except ValidationError as exc:
            errors.extend(exc.messages)
        if rule.max_score <= 0:
            errors.append(f"Điểm tối đa của {rule.question_type} phải lớn hơn 0.")
        if not isinstance(rule.configuration, dict):
            errors.append(f"Cấu hình của {rule.question_type} phải là một object JSON.")

    if blueprint_version is not None:
        required = set(blueprint_version.sections.values_list("slots__question_type", flat=True))
        available = {rule.question_type for rule in rules}
        missing = sorted(required - available)
        if missing:
            errors.append("Thiếu quy tắc chấm cho: " + ", ".join(missing))
        if version.total_score != blueprint_version.expected_total_score:
            errors.append("Tổng điểm của quy tắc chấm không khớp tổng điểm ma trận.")
    if errors:
        raise ValidationError(errors)
    return rules


@transaction.atomic
def lock_scoring_version(version, *, blueprint_version=None, actor=None):
    source = version
    locked_version = ScoringSchemeVersion.objects.select_for_update().get(pk=source.pk)
    if locked_version.is_locked:
        source.is_locked = True
        return version
    validate_scoring_version(locked_version, blueprint_version=blueprint_version)
    # Deliberately bypass model/form/inline saves: locking changes only the parent.
    ScoringSchemeVersion.objects.filter(pk=locked_version.pk, is_locked=False).update(is_locked=True)
    source.is_locked = True
    AssessmentAuditLog.objects.create(
        action="LOCK_SCORING_VERSION", actor=actor, object_type="ScoringSchemeVersion",
        object_id=str(source.pk), details={"blueprint_version_id": getattr(blueprint_version, "pk", None)},
    )
    return source


@transaction.atomic
def clone_scoring_version(source, *, actor=None):
    source = ScoringSchemeVersion.objects.select_for_update().get(pk=source.pk)
    next_version = (source.scheme.versions.aggregate(value=Max("version"))["value"] or 0) + 1
    clone = ScoringSchemeVersion.objects.create(
        scheme=source.scheme, version=next_version, total_score=source.total_score,
        rounding_digits=source.rounding_digits, source_policy_id=source.source_policy_id,
        source_snapshot=deepcopy(source.source_snapshot), created_by=actor, is_locked=False,
    )
    ScoringRule.objects.bulk_create([
        ScoringRule(
            version=clone, question_type=rule.question_type, rule_code=rule.rule_code,
            max_score=rule.max_score, configuration=deepcopy(rule.configuration), order=rule.order,
        ) for rule in source.rules.order_by("order", "pk")
    ])
    AssessmentAuditLog.objects.create(
        action="CLONE_SCORING_VERSION", actor=actor, object_type="ScoringSchemeVersion",
        object_id=str(clone.pk), details={"source_version_id": source.pk},
    )
    return clone
