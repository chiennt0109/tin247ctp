from django.db import transaction
from django.utils import timezone

from assessment.models import AssessmentAuditLog, ExamSession, GeneratedExam
from assessment.services.blueprint_versioning import lock_blueprint_version
from assessment.services.exam_generator import ExamGenerator


@transaction.atomic
def publish_exam_session(session, *, actor=None, base_seed="assessment"):
    session = ExamSession.objects.select_for_update().select_related(
        "blueprint_version", "scoring_version"
    ).get(pk=session.pk)
    if session.status != ExamSession.Status.DRAFT:
        raise ValueError("Only draft exam sessions can be published")
    session.full_clean()
    if session.scoring_version.total_score != session.blueprint_version.expected_total_score:
        raise ValueError("Scoring total does not match blueprint total")
    if not session.blueprint_version.is_locked:
        lock_blueprint_version(
            session.blueprint_version, scoring_version=session.scoring_version, approver=actor,
        )
    if not session.scoring_version.is_locked:
        session.scoring_version.is_locked = True
        session.scoring_version.save(update_fields=("is_locked",))
    exams = ExamGenerator().generate_codes(session, base_seed=base_seed, actor=actor)
    now = timezone.now()
    session.status = ExamSession.Status.OPEN if session.opens_at <= now < session.closes_at else ExamSession.Status.SCHEDULED
    session.published_at = now
    session.save(update_fields=("status", "published_at", "updated_at"))
    GeneratedExam.objects.filter(session=session).update(is_locked=True)
    AssessmentAuditLog.objects.create(
        action="PUBLISH_EXAM_SESSION", actor=actor, object_type="ExamSession",
        object_id=str(session.pk), details={"generated_exam_ids": [exam.pk for exam in exams]},
    )
    return session, exams
