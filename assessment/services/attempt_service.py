import secrets
from contextlib import contextmanager

from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from assessment.models import AttemptAnswer, ExamAttempt, GeneratedExamQuestion


class AttemptStateError(ValueError):
    pass


class StaleAttemptVersion(AttemptStateError):
    pass


def _owned_attempt(attempt_id, user):
    # Do not select_related() the nullable generated_exam while locking. On
    # PostgreSQL that becomes a LEFT OUTER JOIN and SELECT ... FOR UPDATE then
    # fails with: "FOR UPDATE cannot be applied to the nullable side of an
    # outer join". The services only need generated_exam_id, which is already
    # stored on the attempt row being locked.
    return ExamAttempt.objects.select_for_update().get(pk=attempt_id, user=user)


@transaction.atomic
def save_answers(*, attempt_id, user, expected_version, answers):
    attempt = _owned_attempt(attempt_id, user)
    if attempt.status != ExamAttempt.Status.IN_PROGRESS:
        raise AttemptStateError("Bài làm không còn ở trạng thái có thể chỉnh sửa.")
    if timezone.now() >= attempt.expires_at:
        attempt.status = ExamAttempt.Status.AUTO_SUBMITTED
        attempt.submitted_at = timezone.now()
        attempt.save(update_fields=("status", "submitted_at"))
        raise AttemptStateError("Bài làm đã hết giờ và được tự động nộp.")
    if expected_version != attempt.data_version:
        raise StaleAttemptVersion(
            f"Phiên bản cũ: client={expected_version}, server={attempt.data_version}."
        )
    question_ids = {item.get("question_id") for item in answers}
    questions = {
        question.pk: question for question in GeneratedExamQuestion.objects.filter(
            exam_id=attempt.generated_exam_id, pk__in=question_ids
        )
    }
    if None in question_ids or len(questions) != len(question_ids):
        raise AttemptStateError("Có câu trả lời không thuộc đề được cấp.")
    for item in answers:
        answer = item.get("answer", {})
        if not isinstance(answer, dict):
            raise AttemptStateError("Định dạng câu trả lời không hợp lệ.")
        AttemptAnswer.objects.update_or_create(
            attempt=attempt,
            exam_question=questions[item["question_id"]],
            defaults={
                "answer": answer,
                "flagged_for_review": bool(item.get("flagged_for_review", False)),
            },
        )
    attempt.data_version += 1
    attempt.save(update_fields=("data_version",))
    return attempt


@contextmanager
def _submit_lock(attempt_id):
    key = f"assessment:submit:{attempt_id}"
    token = secrets.token_urlsafe(16)
    if not cache.add(key, token, timeout=30):
        raise AttemptStateError("Yêu cầu nộp bài đang được xử lý.")
    try:
        yield
    finally:
        if cache.get(key) == token:
            cache.delete(key)


def submit_attempt(*, attempt_id, user):
    with _submit_lock(attempt_id):
        with transaction.atomic():
            attempt = _owned_attempt(attempt_id, user)
            if attempt.status in {
                ExamAttempt.Status.SUBMITTED,
                ExamAttempt.Status.AUTO_SUBMITTED,
                ExamAttempt.Status.GRADED,
            }:
                return attempt
            if attempt.status != ExamAttempt.Status.IN_PROGRESS:
                raise AttemptStateError("Bài làm không thể nộp ở trạng thái hiện tại.")
            now = timezone.now()
            attempt.status = (
                ExamAttempt.Status.AUTO_SUBMITTED
                if now >= attempt.expires_at
                else ExamAttempt.Status.SUBMITTED
            )
            attempt.submitted_at = now
            attempt.save(update_fields=("status", "submitted_at"))
            return attempt
