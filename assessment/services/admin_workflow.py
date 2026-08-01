from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from assessment.models import ExamBlueprint, ExamSession, ScoringSchemeVersion
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.blueprint_versioning import lock_blueprint_version
from assessment.services.equivalence import validate_equivalence_group
from assessment.services.scoring_versioning import lock_scoring_version, validate_scoring_version


def _scoring_candidates(blueprint, version):
    candidates = ScoringSchemeVersion.objects.filter(
        total_score=version.expected_total_score,
    ).select_related("scheme").order_by("-is_locked", "-version", "-pk")
    policy_id = str(version.source_snapshot.get("POLICY_PROFILE_ID") or "")
    if policy_id:
        policy = candidates.filter(source_policy_id=policy_id)
        if policy.exists():
            return policy
    named = candidates.filter(scheme__name=f"{blueprint.name} — Quy tắc chấm")
    return named if named.exists() else candidates


@transaction.atomic
def prepare_blueprint(blueprint, *, actor=None):
    """Validate and lock the current blueprint/scoring pair through one workflow."""
    blueprint = ExamBlueprint.objects.select_for_update().get(pk=blueprint.pk)
    version = blueprint.versions.order_by("-version").first()
    if version is None:
        raise ValidationError("Ma trận chưa có phiên bản để khóa.")
    scoring_version = None
    for candidate in _scoring_candidates(blueprint, version):
        try:
            validate_scoring_version(candidate, blueprint_version=version)
        except ValidationError:
            continue
        scoring_version = candidate
        break
    if scoring_version is None:
        raise ValidationError("Không có quy tắc chấm phù hợp với ma trận.")
    if not scoring_version.is_locked:
        lock_scoring_version(scoring_version, blueprint_version=version, actor=actor)
    if not version.is_locked:
        lock_blueprint_version(version, scoring_version=scoring_version, approver=actor)
    else:
        report = BlueprintValidator().validate(version, scoring_version=scoring_version)
        if not report["valid"]:
            raise ValidationError(BlueprintValidator.format_failure(report))
        ExamBlueprint.objects.filter(pk=blueprint.pk).update(
            total_questions=version.expected_question_count,
            total_score=version.expected_total_score,
            duration_minutes=version.duration_minutes,
            is_locked=True, is_ready=True,
        )
    for group in blueprint.equivalence_groups.all():
        validate_equivalence_group(group)
    blueprint.refresh_from_db()
    return blueprint


def validate_session_ready(session):
    if session.blueprint_group_id:
        rows = validate_equivalence_group(session.blueprint_group)
        if not any(row["ready"] for row in rows):
            raise ValidationError("Nhóm chưa có ma trận READY + LOCKED đủ nguồn câu.")
        return rows
    report = BlueprintValidator().validate(
        session.blueprint_version, scoring_version=session.scoring_version,
    )
    if not session.blueprint_version.is_locked or not session.scoring_version.is_locked:
        raise ValidationError("Ma trận và quy tắc chấm phải được khóa trước khi mở kỳ thi.")
    if not report["valid"]:
        raise ValidationError(BlueprintValidator.format_failure(report))
    return report


@transaction.atomic
def open_exam_session(session):
    session = ExamSession.objects.select_for_update().get(pk=session.pk)
    validate_session_ready(session)
    now = timezone.now()
    if now >= session.closes_at:
        raise ValidationError("Kỳ thi đã quá thời gian đóng.")
    session.status = (
        ExamSession.Status.OPEN if session.opens_at <= now else ExamSession.Status.SCHEDULED
    )
    if session.published_at is None:
        session.published_at = now
    session.save(update_fields=("status", "published_at", "updated_at"))
    return session


@transaction.atomic
def close_exam_session(session):
    session = ExamSession.objects.select_for_update().get(pk=session.pk)
    if session.status not in {ExamSession.Status.CANCELLED, ExamSession.Status.CLOSED}:
        session.status = ExamSession.Status.CLOSED
        session.save(update_fields=("status", "updated_at"))
    return session
