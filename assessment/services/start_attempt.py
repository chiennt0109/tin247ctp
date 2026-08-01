import hashlib
import secrets
import random
from contextlib import contextmanager
from datetime import timedelta

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from assessment.models import AssessmentAuditLog, ExamAttempt, ExamSession
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.exam_generator import ExamGenerationError, ExamGenerator
from assessment.services.equivalence import validate_equivalence_group
from assessment.services.session_configuration import resolve_locked_configuration
from assessment.services.access_grants import resolve_exam_access


class StartAttemptError(ValueError):
    pass


@contextmanager
def _start_lock(session_id, user_id):
    key = f"assessment:start:{session_id}:{user_id}"
    token = secrets.token_urlsafe(16)
    if not cache.add(key, token, timeout=30):
        raise StartAttemptError("Yêu cầu bắt đầu đang được xử lý, vui lòng thử lại.")
    try:
        yield
    finally:
        if cache.get(key) == token:
            cache.delete(key)


def _user_grade(user):
    for owner in (user, getattr(user, "profile", None)):
        if owner is not None and getattr(owner, "grade", None) is not None:
            return str(owner.grade)
    return None


def user_can_access_session(user, session):
    return resolve_exam_access(
        user, session, timezone.now(), user_grade=_user_grade(user),
    ).allowed


def _generation_identity(session, user, attempt_number):
    nonce = secrets.token_hex(16)
    seed = hashlib.sha256(
        f"{session.pk}:{user.pk}:{attempt_number}:{nonce}".encode()
    ).hexdigest()
    return seed, f"U{user.pk}-A{attempt_number}"


def _group_configuration(session, user):
    rows = validate_equivalence_group(session.blueprint_group)
    candidates = [row for row in rows if row["ready"] and row["version"] is not None]
    if not candidates:
        raise StartAttemptError(
            "Chưa có ma trận đủ nguồn câu để sinh đề. "
            f"Nhóm '{session.blueprint_group}' không có ma trận READY + LOCKED."
        )

    # Do not repeat a matrix for the same student until every currently-ready
    # matrix in the group has been used. Selection inside each cycle remains
    # cryptographically random and is independent for every user.
    used_blueprints = set(
        ExamAttempt.objects.filter(user=user, session=session)
        .exclude(status=ExamAttempt.Status.INVALIDATED)
        .values_list("blueprint_id", flat=True)
    )
    unused = [row for row in candidates if row["blueprint"].pk not in used_blueprints]
    selected = secrets.choice(unused or candidates)
    blueprint_version, scoring_version = resolve_locked_configuration(selected["blueprint"])
    return blueprint_version, scoring_version


def start_attempt(user, exam_session):
    with _start_lock(exam_session.pk, user.pk):
        try:
            with transaction.atomic():
                session = ExamSession.objects.select_for_update().select_related(
                    "blueprint_version", "scoring_version"
                ).get(pk=exam_session.pk)
                now = timezone.now()
                if (
                    session.status == ExamSession.Status.SCHEDULED
                    and session.opens_at <= now < session.closes_at
                ):
                    session.status = ExamSession.Status.OPEN
                    session.save(update_fields=("status", "updated_at"))
                if session.status != ExamSession.Status.OPEN:
                    raise StartAttemptError("Kỳ kiểm tra chưa mở hoặc đã đóng.")
                opens_at = session.opens_at
                closes_at = session.closes_at
                if now < opens_at or now >= closes_at:
                    raise StartAttemptError("Ngoài thời gian làm bài.")
                access = resolve_exam_access(
                    user, session, now, user_grade=_user_grade(user),
                )
                if not access.allowed:
                    raise StartAttemptError(access.reason)
                existing = ExamAttempt.objects.select_related("generated_exam").filter(
                    user=user, session=session, status=ExamAttempt.Status.IN_PROGRESS
                ).first()
                if existing:
                    if timezone.now() >= existing.expires_at:
                        existing.status = ExamAttempt.Status.EXPIRED
                        existing.save(update_fields=("status",))
                        existing = None
                if existing:
                    if existing.generated_exam_id is None:
                        raise StartAttemptError("Bài làm đang mở không có đề; quản trị viên cần kiểm tra.")
                    return existing

                used = ExamAttempt.objects.filter(user=user, session=session).exclude(
                    status=ExamAttempt.Status.INVALIDATED
                ).count()
                if access.max_attempts is not None and used >= access.max_attempts:
                    raise StartAttemptError("Bạn đã sử dụng hết số lượt làm.")
                attempt_number = used + 1
                duration = session.duration_minutes
                natural_expiry = now + timedelta(minutes=duration)
                deadlines = [natural_expiry, closes_at]
                if access.valid_until:
                    deadlines.append(access.valid_until)
                expires_at = min(deadlines)
                seed, code = _generation_identity(session, user, attempt_number)
                blueprint_version = session.blueprint_version
                scoring_version = session.scoring_version
                if session.blueprint_group_id:
                    blueprint_version, scoring_version = _group_configuration(session, user)
                validation = BlueprintValidator().validate(
                    blueprint_version, scoring_version=scoring_version
                )
                if not validation["valid"]:
                    detail = BlueprintValidator.format_failure(validation)
                    raise StartAttemptError(f"Không thể sinh đề: {detail}")
                exam = ExamGenerator().generate_for_attempt(
                    session, code=code, seed=seed, actor=user,
                    blueprint_version=blueprint_version, scoring_version=scoring_version,
                )
                attempt = ExamAttempt.objects.create(
                    user=user, session=session, attempt_number=attempt_number,
                    expires_at=expires_at, generated_exam=exam,
                    blueprint=blueprint_version.blueprint, blueprint_version=blueprint_version,
                )
                AssessmentAuditLog.objects.create(
                    action="START_ATTEMPT", actor=user, object_type="ExamAttempt",
                    object_id=str(attempt.pk), details={
                        "generated_exam_id": exam.pk,
                        "blueprint_id": blueprint_version.blueprint_id,
                        "blueprint_version_id": blueprint_version.pk,
                        "access_grant_id": access.grant_id,
                        "effective_max_attempts": access.max_attempts,
                        "access_valid_until": (
                            access.valid_until.isoformat() if access.valid_until else None
                        ),
                    },
                )
                return attempt
        except IntegrityError as exc:
            existing = ExamAttempt.objects.filter(
                user=user, session=exam_session, status=ExamAttempt.Status.IN_PROGRESS
            ).first()
            if existing:
                return existing
            raise StartAttemptError("Không thể tạo bài làm do xung đột dữ liệu.") from exc
        except ExamGenerationError as exc:
            raise StartAttemptError(str(exc)) from exc
