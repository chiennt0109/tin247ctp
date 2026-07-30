import json

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from assessment.models import ExamAttempt, ExamParticipant, ExamSession, GradingResult
from assessment.models import AssessmentAuditLog
from assessment.services.analytics import exam_results_dashboard, official_attempts, student_result_summary
from assessment.services.attempt_service import (
    AttemptStateError, StaleAttemptVersion, save_answers, submit_attempt,
)
from assessment.services.start_attempt import StartAttemptError, start_attempt, user_can_access_session
from assessment.services.result_release import result_visibility


def exam_list_redirect(request):
    return redirect("assessment:exam_list")


def _rate_limited(key, *, limit, window):
    cache_key = f"assessment:rate:{key}"
    if cache.add(cache_key, 1, timeout=window):
        return False
    try:
        return cache.incr(cache_key) > limit
    except ValueError:
        cache.set(cache_key, 1, timeout=window)
        return False


@login_required
def exam_list(request):
    """Show sessions allowed by session policy plus per-user overrides."""
    sessions = (
        ExamSession.objects.filter(is_demo=False).exclude(
            status__in=(ExamSession.Status.DRAFT, ExamSession.Status.CANCELLED),
        )
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
        latest_result = ExamAttempt.objects.filter(
            user=request.user, session=session, status=ExamAttempt.Status.GRADED,
        ).order_by("-attempt_number").first()
        cards.append({
            "session": session, "participant": participant, "attempts_used": session.attempts_used,
            "attempts_remaining": max(maximum - session.attempts_used, 0), "active_attempt": active,
            "latest_result": latest_result,
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
    return redirect("assessment:attempt_detail", attempt_id=attempt.pk)


@login_required
def attempt_detail(request, attempt_id):
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("session", "generated_exam"), pk=attempt_id
    )
    if attempt.user_id != request.user.pk and not request.user.is_staff:
        raise Http404
    if attempt.status != ExamAttempt.Status.IN_PROGRESS:
        messages.info(request, "Bài làm này đã kết thúc.")
        return redirect("assessment:exam_list")
    if timezone.now() >= attempt.expires_at:
        submit_attempt(attempt_id=attempt.pk, user=attempt.user)
        messages.info(request, "Bài làm đã hết giờ và được tự động nộp.")
        return redirect("assessment:exam_list")
    questions = list(attempt.generated_exam.questions.only(
        "order", "stem_snapshot", "options_snapshot", "statements_snapshot"
    ).order_by("order"))
    saved = {answer.exam_question_id: answer for answer in attempt.answers.all()}
    question_rows = [{"question": question, "saved": saved.get(question.pk)} for question in questions]
    return render(request, "assessment/attempt.html", {
        "attempt": attempt, "question_rows": question_rows,
        "server_now_ms": int(timezone.now().timestamp() * 1000),
        "expires_at_ms": int(attempt.expires_at.timestamp() * 1000),
    })


@login_required
@require_http_methods(["PATCH"])
def autosave_answers(request, attempt_id):
    if _rate_limited(f"save:{request.user.pk}:{attempt_id}", limit=30, window=10):
        return JsonResponse({"error": "Quá nhiều yêu cầu lưu."}, status=429)
    if len(request.body) > 64 * 1024:
        return JsonResponse({"error": "Payload quá lớn."}, status=413)
    try:
        payload = json.loads(request.body or b"{}")
        version = int(payload["version"])
        answers = payload.get("answers", [])
        if not isinstance(answers, list) or len(answers) > 100:
            raise ValueError
        attempt = save_answers(
            attempt_id=attempt_id, user=request.user,
            expected_version=version, answers=answers,
        )
    except ExamAttempt.DoesNotExist:
        raise Http404
    except StaleAttemptVersion as exc:
        current = ExamAttempt.objects.only("data_version").get(pk=attempt_id, user=request.user)
        return JsonResponse({"error": str(exc), "version": current.data_version}, status=409)
    except (AttemptStateError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc) or "Dữ liệu không hợp lệ."}, status=400)
    return JsonResponse({"saved": True, "version": attempt.data_version})


@login_required
@require_POST
def submit_attempt_view(request, attempt_id):
    if _rate_limited(f"submit:{request.user.pk}:{attempt_id}", limit=5, window=60):
        return JsonResponse({"error": "Quá nhiều yêu cầu nộp bài."}, status=429)
    try:
        attempt = submit_attempt(attempt_id=attempt_id, user=request.user)
    except ExamAttempt.DoesNotExist:
        raise Http404
    except AttemptStateError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse({
        "submitted": True, "status": attempt.status,
        "submitted_at": attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        "result_url": reverse("assessment:attempt_result", args=(attempt.pk,)),
    })


@login_required
def attempt_state(request, attempt_id):
    attempt = get_object_or_404(ExamAttempt, pk=attempt_id, user=request.user)
    return JsonResponse({
        "status": attempt.status, "version": attempt.data_version,
        "server_now_ms": int(timezone.now().timestamp() * 1000),
        "expires_at_ms": int(attempt.expires_at.timestamp() * 1000),
    })


@login_required
def attempt_result(request, attempt_id):
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("session", "user"), pk=attempt_id,
    )
    if attempt.user_id != request.user.pk and not request.user.has_perm("assessment.view_results"):
        raise Http404
    if attempt.status != ExamAttempt.Status.GRADED:
        messages.info(request, "Bài làm chưa có kết quả chấm.")
        return redirect("assessment:exam_list")
    result = get_object_or_404(
        GradingResult, attempt=attempt, is_current=True,
    )
    participant = ExamParticipant.objects.filter(session=attempt.session, user=attempt.user).first()
    visibility = result_visibility(attempt, participant=participant)
    if request.user.has_perm("assessment.view_results"):
        visibility = {"score": True, "answers": True, "solutions": True, "review": True}
    summary = student_result_summary(attempt)
    attempts = list(ExamAttempt.objects.filter(
        user=attempt.user, session=attempt.session, status=ExamAttempt.Status.GRADED,
    ).order_by("attempt_number"))
    official = official_attempts(attempts, attempt.session.attempt_result_mode)
    return render(request, "assessment/result.html", {
        "attempt": attempt, "result": result, "visibility": visibility,
        "summary": summary, "attempts": attempts, "official_attempt_ids": official,
    })


@login_required
def result_list(request):
    attempts = list(ExamAttempt.objects.filter(
        user=request.user, status=ExamAttempt.Status.GRADED, session__is_demo=False,
    ).select_related("session").prefetch_related("grading_results").order_by("-submitted_at"))
    by_session = {}
    for attempt in attempts:
        by_session.setdefault(attempt.session_id, []).append(attempt)
    official = set()
    for rows in by_session.values():
        official |= official_attempts(rows, rows[0].session.attempt_result_mode)
    rows = []
    for attempt in attempts:
        participant = ExamParticipant.objects.filter(session=attempt.session, user=request.user).first()
        rows.append({
            "attempt": attempt, "visibility": result_visibility(attempt, participant=participant),
            "official": attempt.pk in official,
        })
    return render(request, "assessment/result_list.html", {"result_rows": rows})


@login_required
def manage_exam_results(request, session_id):
    if not request.user.has_perm("assessment.view_results"):
        raise Http404
    session = get_object_or_404(ExamSession, pk=session_id)
    return render(request, "assessment/manage_results.html", {
        "session": session, "dashboard": exam_results_dashboard(session),
    })


@login_required
@require_POST
def manage_result_release(request, session_id, target, action):
    permission = "assessment.release_results" if target == "score" else "assessment.release_answers"
    if not request.user.has_perm(permission):
        raise Http404
    fields = {
        "score": "results_released_at", "answers": "answers_released_at",
        "solutions": "solutions_released_at",
    }
    field = fields.get(target)
    if not field or action not in {"release", "revoke"}:
        raise Http404
    session = get_object_or_404(ExamSession, pk=session_id)
    setattr(session, field, timezone.now() if action == "release" else None)
    session.save(update_fields=(field,))
    AssessmentAuditLog.objects.create(
        action=f"{action.upper()}_{target.upper()}", actor=request.user,
        object_type="ExamSession", object_id=str(session.pk),
        details={"field": field},
    )
    messages.success(request, "Đã cập nhật trạng thái công bố.")
    return redirect("assessment:manage_exam_results", session_id=session.pk)
