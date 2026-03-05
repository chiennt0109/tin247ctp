# path: submissions/views.py
import os
import json
import hashlib

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

from redis import Redis
from rq import Queue

from .models import Submission
from problems.models import Problem
from judge.grader import grade_submission
from contests.utils import update_participation
from .tasks import judge_submission  # 🔑 chỉ dùng job này

from django.utils import timezone
from contests.models import Contest, PracticeSession


# ============================
# ⚙️ Cấu hình Redis / Sandbox
# ============================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
USE_SANDBOX = True

LOCK_TTL = 5      # chặn double–click trong 5s
IDEMP_TTL = 30    # cùng 1 code trong 30s → dùng lại submission cũ


def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()


# ======================================================
# 🧾 TRANG HIỂN THỊ NỘP BÀI
# URL: /submissions/<problem_id>/
# ======================================================
@login_required
def submission_page(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)

    contest_id = request.GET.get("contest_id", "").strip()
    practice = request.GET.get("practice") == "1"

    remaining = None

    # Nếu đang ở PRACTICE MODE
    if practice and contest_id:
        sess = PracticeSession.objects.filter(
            contest_id=contest_id,
            user=request.user,
            is_started=True,
            is_locked=False,
            cancelled=False,
        ).order_by("-created_at").first()

        if sess:
            remaining = sess.remaining_seconds
            if remaining < 0:
                remaining = 0

    return render(
        request,
        "submissions/submit.html",
        {
            "problem": problem,
            "contest_id": contest_id,
            "practice": practice,
            "remaining": remaining,
        },
    )


# ======================================================
# 🚀 XỬ LÝ NỘP BÀI — NORMAL / CONTEST / PRACTICE
# URL: /submissions/<problem_id>/submit/
# ======================================================
@login_required
def submission_create(request, problem_id):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)

    problem = get_object_or_404(Problem, pk=problem_id)

    lang = (request.POST.get("language") or "").strip()
    code = request.POST.get("source") or ""

    contest_id = request.POST.get("contest_id", "").strip()
    is_practice = request.POST.get("practice") == "1"

    if not lang or not code:
        return JsonResponse(
            {"ok": False, "error": "Thiếu ngôn ngữ hoặc mã nguồn."},
            status=400,
        )

    # =====================================================
    # 🔥 LOAD CONTEST (nếu có)
    # =====================================================
    contest = None
    if contest_id:
        try:
            contest = Contest.objects.get(id=contest_id)
        except Contest.DoesNotExist:
            contest = None

    # =====================================================
    # 🎯 GUARD CHO CONTEST CHÍNH
    # =====================================================
    if contest and not is_practice:
        now = timezone.now()
        if now > contest.end_time:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Cuộc thi đã kết thúc. Bạn không thể nộp bài.",
                },
                status=403,
            )

    # =====================================================
    # 🔥 PRACTICE MODE → lấy session hợp lệ
    # =====================================================
    practice_session = None
    if is_practice and contest:
        practice_session = PracticeSession.objects.filter(
            contest=contest,
            user=request.user,
            is_started=True,
            is_locked=False,
            cancelled=False,
        ).order_by("-created_at").first()

        # chưa có hoặc đã bị khoá
        if not practice_session:
            return JsonResponse(
                {
                    "ok": False,
                    "error": "Phiên PRACTICE của bạn chưa bắt đầu hoặc đã hết giờ.",
                },
                status=403,
            )

        # hết giờ → khoá lại và chặn
        if practice_session.remaining_seconds == 0:
            practice_session.is_locked = True
            practice_session.save(update_fields=["is_locked"])
            return JsonResponse(
                {"ok": False, "error": "Phiên PRACTICE đã hết giờ."},
                status=403,
            )

    # =====================================================
    # 🔒 REDIS LOCK + IDEMPOTENCY
    # =====================================================
    user_id = request.user.id
    lock_key = f"submit:lock:u{user_id}:p{problem_id}"
    code_key = f"submit:idem:u{user_id}:p{problem_id}:sha1:{_sha1(code)}"

    try:
        r = Redis.from_url(REDIS_URL)
    except Exception:
        r = None

    if r:
        # lock chống double-click
        if not r.set(lock_key, "1", nx=True, ex=LOCK_TTL):
            return JsonResponse(
                {
                    "ok": False,
                    "error": f"Bạn đang nộp quá nhanh, vui lòng đợi {LOCK_TTL}s.",
                    "retry_after": LOCK_TTL,
                },
                status=429,
            )

        # idempotent theo code
        existing = r.get(code_key)
        if existing:
            return JsonResponse(
                {
                    "ok": True,
                    "submission_id": int(existing.decode("utf-8")),
                    "idempotent": True,
                }
            )

    # =====================================================
    # ⭐ Tạo SUBMISSION mới
    # =====================================================
    sub = Submission.objects.create(
        user=request.user,
        problem=problem,
        language=lang,
        source_code=code,
        verdict="Pending",
        # gắn contest hoặc practice session
        contest=contest if (contest and not is_practice) else None,
        practice_session=practice_session if is_practice else None,
    )

    # idempotency
    if r:
        try:
            r.set(code_key, str(sub.id), ex=IDEMP_TTL)
        except Exception:
            pass

    # =====================================================
    # 🚀 Đẩy job chấm sang worker
    # =====================================================
    if USE_SANDBOX:
        try:
            if not r:
                r = Redis.from_url(REDIS_URL)
            Queue("judge", connection=r).enqueue(judge_submission, sub.id)
        except Exception as e:
            sub.verdict = "Judge Error"
            sub.debug_info = str(e)
            sub.save()
            _grade_local(sub)
    else:
        _grade_local(sub)

    # =====================================================
    # 📌 UPDATE RANKING — CHỈ CONTEST
    # =====================================================
    if contest and not is_practice:
        update_participation(request.user, problem, contest)

    return JsonResponse(
        {
            "ok": True,
            "submission_id": sub.id,
            "mode": "practice"
            if is_practice
            else "contest"
            if contest
            else "normal",
        }
    )


def _grade_local(sub: Submission):
    """Chấm local khi sandbox chết / lỗi Redis."""
    verdict, exec_time, passed, total, debug = grade_submission(sub)
    sub.verdict = verdict
    sub.exec_time = float(exec_time or 0.0)
    sub.passed_tests = passed
    sub.total_tests = total
    try:
        sub.debug_info = json.dumps(debug, ensure_ascii=False)
    except Exception:
        sub.debug_info = str(debug)
    sub.save()


# ======================================================
# 📜 CHI TIẾT BÀI NỘP
# URL: /submissions/<submission_id>/detail/
# ======================================================
@login_required
def submission_detail(request, submission_id):
    submission = get_object_or_404(Submission, pk=submission_id)

    try:
        submission.debug_info_json = json.loads(submission.debug_info or "[]")
    except Exception:
        submission.debug_info_json = []

    return render(
        request,
        "submissions/detail.html",
        {
            "submission": submission,
            "debug_info_json": submission.debug_info_json,
        },
    )
