from django.utils import timezone

from assessment.models import ExamSession


def is_released(
    mode, session, attempt, *, now=None, manual_at=None, specific_at=None, max_attempts=None,
):
    now = now or timezone.now()
    if mode == ExamSession.ReleaseMode.NEVER:
        return False
    if mode == ExamSession.ReleaseMode.AFTER_SUBMIT:
        return attempt.submitted_at is not None
    if mode == ExamSession.ReleaseMode.AFTER_ALL:
        return attempt.user.assessment_attempts.filter(session=session).exclude(
            status="INVALIDATED",
        ).count() >= (max_attempts or session.max_attempts)
    if mode == ExamSession.ReleaseMode.AFTER_CLOSE:
        return now >= session.closes_at
    if mode == ExamSession.ReleaseMode.AT_TIME:
        return bool(specific_at and now >= specific_at)
    if mode == ExamSession.ReleaseMode.MANUAL:
        return bool(manual_at and now >= manual_at)
    return False


def result_visibility(attempt, *, now=None, participant=None):
    session = attempt.session
    maximum = (
        participant.max_attempts_override
        if participant and participant.max_attempts_override else session.max_attempts
    )
    score = is_released(
        session.score_release_mode, session, attempt, now=now,
        manual_at=session.results_released_at, specific_at=session.score_release_at,
        max_attempts=maximum,
    )
    answers = is_released(
        session.answer_release_mode, session, attempt, now=now,
        manual_at=session.answers_released_at, specific_at=session.answer_release_at,
        max_attempts=maximum,
    )
    if participant and participant.can_view_answers:
        answers = True
    return {
        "score": score,
        "answers": answers,
        "solutions": answers and session.release_solutions and bool(
            not participant or participant.can_view_solutions
        ),
        "review": session.allow_review,
    }
