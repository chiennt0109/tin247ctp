from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from assessment.models import ExamAttempt, ExamParticipant, ExamSession
from assessment.services.start_attempt import StartAttemptError, start_attempt, user_can_access_session


def exam_list_redirect(request):
    return redirect("assessment:exam_list")


@login_required
def exam_list(request):
    """Show sessions allowed by session policy plus per-user overrides."""
    sessions = (
        ExamSession.objects.exclude(status__in=(ExamSession.Status.DRAFT, ExamSession.Status.CANCELLED))
        .select_related("blueprint_version")
        .prefetch_related("access_groups")
        .annotate(
            attempts_used=Count("attempts", filter=Q(attempts__user=request.user) & ~Q(attempts__status="INVALIDATED"))
        )
        .order_by("opens_at", "name")
    )
    participants = {
        item.session_id: item for item in ExamParticipant.objects.filter(
            user=request.user, session__in=sessions
        )
    }
    cards = []
    for session in sessions:
        participant = participants.get(session.pk)
        if not user_can_access_session(request.user, session, participant):
            continue
        maximum = participant.max_attempts_override if participant and participant.max_attempts_override else session.max_attempts
        active = ExamAttempt.objects.filter(
            user=request.user, session=session, status=ExamAttempt.Status.IN_PROGRESS
        ).first()
        cards.append({
            "session": session, "participant": participant, "attempts_used": session.attempts_used,
            "attempts_remaining": max(maximum - session.attempts_used, 0), "active_attempt": active,
        })
    return render(
        request,
        "assessment/exam_list.html",
        {"exam_cards": cards},
    )


@login_required
@require_POST
def start_exam(request, slug):
    session = get_object_or_404(ExamSession, slug=slug)
    try:
        attempt = start_attempt(request.user, session)
    except StartAttemptError as exc:
        messages.error(request, str(exc))
        return redirect("assessment:exam_list")
    return redirect("assessment:attempt_debug", attempt_id=attempt.pk)


@login_required
def attempt_debug(request, attempt_id):
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("session", "generated_exam"), pk=attempt_id
    )
    if attempt.user_id != request.user.pk and not request.user.is_staff:
        raise Http404
    questions = attempt.generated_exam.questions.only(
        "order", "stem_snapshot", "options_snapshot", "statements_snapshot"
    ).order_by("order")
    return render(request, "assessment/attempt_debug.html", {"attempt": attempt, "questions": questions})
