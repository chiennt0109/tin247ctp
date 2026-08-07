import json
import uuid

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from assessment.models import ExamAttempt, ExamResourcePackage, ExamSession, GradingResult
from assessment.models import AssessmentAuditLog
from assessment.services.analytics import exam_results_dashboard, official_attempts, student_result_summary
from assessment.services.attempt_service import (
    AttemptStateError, StaleAttemptVersion, save_answers, submit_attempt,
)
from assessment.services.attempt_downloads import (
    build_attempt_download_zip, user_download_permission,
)
from assessment.services.resource_packages import (
    ResourcePackageError, create_resource_package, download_package_zip,
)
from assessment.services.usage_ledger import usage_breakdown
from assessment.services.start_attempt import StartAttemptError, effective_exam_access, start_attempt
from assessment.services.result_release import result_visibility
from assessment.services.result_presentation import result_sections


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
    """Show exam sessions available through their session-level access policy."""
    sessions = (
        ExamSession.objects.exclude(
            status__in=(ExamSession.Status.DRAFT, ExamSession.Status.CANCELLED),
        )
        .select_related("blueprint_version")
        .prefetch_related("access_groups")
        .order_by("opens_at", "name")
    )
    cards = []
    now = timezone.now()
    for session in sessions:
        access = effective_exam_access(request.user, session, now=now)
        if not access.visible:
            continue
        active = None
        if access.allowed:
            active = ExamAttempt.objects.filter(
                user=request.user, session=session, status=ExamAttempt.Status.IN_PROGRESS
            ).first()
        latest_result = ExamAttempt.objects.filter(
            user=request.user, session=session, status=ExamAttempt.Status.GRADED,
        ).order_by("-attempt_number").first()
        breakdown = usage_breakdown(request.user, session)
        used_total = breakdown["total"]
        attempts_remaining = (
            None if access.max_attempts is None
            else max(access.max_attempts - used_total, 0)
        )
        if "trial_remaining" in breakdown:
            attempts_remaining = (
                breakdown["trial_remaining"] if attempts_remaining is None
                else min(attempts_remaining, breakdown["trial_remaining"])
            )
        unavailable_reason = access.reason
        session_can_start = (
            session.status in {ExamSession.Status.OPEN, ExamSession.Status.SCHEDULED}
            and session.opens_at <= now < session.closes_at
        )
        if access.allowed and not session_can_start:
            unavailable_reason = (
                "Kỳ kiểm tra chưa đến thời gian mở."
                if now < session.opens_at else "Kỳ kiểm tra đã đóng."
            )
        if access.allowed and session_can_start and attempts_remaining == 0:
            unavailable_reason = "Bạn đã sử dụng hết số lượt làm."
        can_start = (
            access.allowed and session_can_start
            and (attempts_remaining is None or attempts_remaining > 0)
        )
        cards.append({
            "session": session, "attempts_used": used_total,
            "usage_breakdown": breakdown, "attempts_remaining": attempts_remaining,
            "download_allowed": user_download_permission(request.user, session).allowed,
            "online_idempotency_key": uuid.uuid4().hex,
            "download_idempotency_key": uuid.uuid4().hex,
            "can_start": can_start, "unavailable_reason": unavailable_reason,
            "active_attempt": active,
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
        attempt = start_attempt(
            request.user, session,
            idempotency_key=request.POST.get("idempotency_key") or None,
        )
    except StartAttemptError as exc:
        messages.error(request, str(exc))
        return redirect("assessment:exam_list")
    return redirect("assessment:attempt_detail", attempt_id=attempt.pk)

@login_required
@require_POST
def create_download_resource(request, slug):
    session = get_object_or_404(ExamSession, slug=slug)
    key = request.POST.get("idempotency_key") or uuid.uuid4().hex
    try:
        package = create_resource_package(request.user, session, idempotency_key=key)
    except ResourcePackageError as exc:
        messages.error(request, str(exc))
        return redirect("assessment:exam_list")
    messages.success(request, "Đã tạo gói đề tải. Bạn có thể tải lại trong Tài nguyên của tôi.")
    return redirect("assessment:my_resources")


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
    if attempt.session.status != ExamSession.Status.OPEN:
        submit_attempt(attempt_id=attempt.pk, user=attempt.user)
        messages.info(request, "Kỳ kiểm tra đã đóng; bài làm đã được tự động nộp.")
        return redirect("assessment:exam_list")
    if timezone.now() >= attempt.expires_at:
        submit_attempt(attempt_id=attempt.pk, user=attempt.user)
        messages.info(request, "Bài làm đã hết giờ và được tự động nộp.")
        return redirect("assessment:exam_list")
    questions = list(attempt.generated_exam.questions.select_related("bank_question").only(
        "order", "stem_snapshot", "options_snapshot", "statements_snapshot",
        "bank_question__question_type",
    ).order_by("order"))
    saved = {answer.exam_question_id: answer for answer in attempt.answers.all()}
    question_rows = [{
        "question": question, "saved": saved.get(question.pk),
        "question_type": question.bank_question.question_type,
    } for question in questions]
    mcq_rows = [row for row in question_rows if row["question_type"] == "MCQ_SINGLE"]
    true_false_rows = [row for row in question_rows if row["question_type"] == "TRUE_FALSE_GROUP"]
    other_rows = [row for row in question_rows if row["question_type"] not in {
        "MCQ_SINGLE", "TRUE_FALSE_GROUP",
    }]
    for rows in (mcq_rows, true_false_rows, other_rows):
        for part_order, row in enumerate(rows, start=1):
            row["part_order"] = part_order
    download_permission = user_download_permission(request.user, attempt.session)
    return render(request, "assessment/attempt.html", {
        "attempt": attempt, "question_rows": question_rows,
        "mcq_rows": mcq_rows, "true_false_rows": true_false_rows, "other_rows": other_rows,
        "server_now_ms": int(timezone.now().timestamp() * 1000),
        "expires_at_ms": int(attempt.expires_at.timestamp() * 1000),
        "allow_attempt_download": download_permission.allowed,
        "allow_attempt_answer_download": False,
    })



def _session_answers_released(session, *, now=None):
    now = now or timezone.now()
    return (
        (session.answer_release_mode == ExamSession.ReleaseMode.AFTER_CLOSE and now >= session.closes_at)
        or (session.answer_release_mode == ExamSession.ReleaseMode.MANUAL and bool(session.answers_released_at))
        or (
            session.answer_release_mode == ExamSession.ReleaseMode.AT_TIME
            and bool(session.answer_release_at and now >= session.answer_release_at)
        )
    )

@login_required
def my_resources(request):
    attempts = ExamAttempt.objects.filter(user=request.user).select_related(
        "session", "generated_exam", "blueprint_version",
    ).order_by("-started_at")
    attempt_rows = [
        {"attempt": attempt, "visibility": result_visibility(attempt)}
        for attempt in attempts
    ]
    packages = ExamResourcePackage.objects.filter(user=request.user).select_related(
        "session", "generated_exam", "blueprint_version",
    ).order_by("session__name", "-created_at")
    package_rows = [
        {"package": package, "answers_released": _session_answers_released(package.session)}
        for package in packages
    ]
    attempt_page = Paginator(attempt_rows, 20).get_page(request.GET.get("attempt_page"))
    package_page = Paginator(package_rows, 20).get_page(request.GET.get("package_page"))
    return render(request, "assessment/my_resources.html", {
        "attempt_page": attempt_page, "package_page": package_page,
    })


@login_required
def download_resource_package(request, package_id, package):
    resource = get_object_or_404(
        ExamResourcePackage.objects.select_related("session", "generated_exam", "blueprint"),
        pk=package_id, user=request.user, status=ExamResourcePackage.Status.READY,
    )
    variants = request.GET.get("variants", "1")
    if package == "exam_answers" and not _session_answers_released(resource.session):
        raise Http404
    try:
        payload = download_package_zip(resource, request.user, package_type=package, variants=variants)
    except PermissionDenied:
        raise Http404
    except ValidationError as exc:
        return JsonResponse({"error": "; ".join(exc.messages)}, status=400)
    response = HttpResponse(payload, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="GOI_DE_{resource.generated_exam.code}.zip"'
    )
    response["Cache-Control"] = "no-store"
    return response


@login_required
def download_attempt_package(request, attempt_id, package):
    attempt = get_object_or_404(
        ExamAttempt.objects.select_related("session"), pk=attempt_id, user=request.user,
    )
    variants = request.GET.get("variants", "1")
    if package == "exam_answers" and not result_visibility(attempt)["answers"]:
        raise Http404
    try:
        payload = build_attempt_download_zip(
            attempt=attempt, user=request.user, package=package, variants=variants,
        )
    except PermissionDenied:
        raise Http404
    except ValidationError as exc:
        return JsonResponse({"error": "; ".join(exc.messages)}, status=400)
    response = HttpResponse(payload, content_type="application/zip")
    response["Content-Disposition"] = (
        f'attachment; filename="GOI_DE_{attempt.generated_exam.code}.zip"'
    )
    response["Cache-Control"] = "no-store"
    return response


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
        "allow_attempt_download": download_permission.allowed,
        "allow_attempt_answer_download": False,
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
    visibility = result_visibility(attempt)
    if attempt.user_id != request.user.pk and request.user.has_perm("assessment.view_results"):
        visibility = {"score": True, "answers": True, "solutions": True, "review": True}
    summary = student_result_summary(attempt)
    detail_sections = result_sections(
        attempt, result, include_correct_answers=visibility["answers"],
    ) if visibility["score"] else []
    attempts = list(ExamAttempt.objects.filter(
        user=attempt.user, session=attempt.session, status=ExamAttempt.Status.GRADED,
    ).order_by("attempt_number"))
    official = official_attempts(attempts, attempt.session.attempt_result_mode)
    return render(request, "assessment/result.html", {
        "attempt": attempt, "result": result, "visibility": visibility,
        "summary": summary, "detail_sections": detail_sections,
        "attempts": attempts, "official_attempt_ids": official,
    })


@login_required
def result_list(request):
    attempts = list(ExamAttempt.objects.filter(
        user=request.user, status=ExamAttempt.Status.GRADED,
    ).select_related("session").prefetch_related("grading_results").order_by("-submitted_at"))
    by_session = {}
    for attempt in attempts:
        by_session.setdefault(attempt.session_id, []).append(attempt)
    official = set()
    for rows in by_session.values():
        official |= official_attempts(rows, rows[0].session.attempt_result_mode)
    rows = []
    for attempt in attempts:
        rows.append({
            "attempt": attempt, "visibility": result_visibility(attempt),
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
