# path: submissions/views.py
import os
import json
import hashlib

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.views.decorators.http import require_POST

from redis import Redis

from .models import Submission
from problems.models import Problem, TestCase
from judge.dispatcher import JudgeDispatcher
from judge.runner import compile_submission, run_case
from judge.sandbox import SandboxManager
from contests.utils import update_participation

from django.utils import timezone
from contests.models import Contest, PracticeSession


# ============================
# ⚙️ Cấu hình Redis / Sandbox
# ============================
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
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
            "sample_tests": TestCase.objects.filter(
                problem=problem, is_sample=True
            ).order_by("id"),
        },
    )


@login_required
@require_POST
def run_sample(request, problem_id):
    """Compile and run one public sample (or bounded custom input) in the judge sandbox."""
    problem = get_object_or_404(Problem, pk=problem_id)
    language = (request.POST.get("language") or "").strip()
    source = request.POST.get("source") or ""
    sample_id = (request.POST.get("sample_id") or "").strip()

    if language not in {"cpp", "python", "pypy"}:
        return JsonResponse({"ok": False, "error": "Ngôn ngữ không được hỗ trợ."}, status=400)
    if not source.strip() or len(source.encode("utf-8")) > 100_000:
        return JsonResponse({"ok": False, "error": "Mã nguồn trống hoặc vượt quá 100 KB."}, status=400)

    throttle_key = f"sample-run:{request.user.pk}"
    if not cache.add(throttle_key, "1", timeout=3):
        return JsonResponse({"ok": False, "error": "Vui lòng đợi 3 giây trước lần chạy tiếp theo."}, status=429)

    expected = None
    if sample_id:
        sample = get_object_or_404(TestCase, pk=sample_id, problem=problem, is_sample=True)
        input_data, expected = sample.input_data, sample.expected_output
    else:
        # Bài cũ chưa có test ví dụ: chỉ nhận stdin dạng văn bản, không bao giờ
        # đưa nội dung này vào shell command hoặc ghi vào bộ test chính thức.
        input_data = request.POST.get("custom_input") or ""
        if len(input_data.encode("utf-8")) > 64_000:
            return JsonResponse({"ok": False, "error": "Dữ liệu vào vượt quá 64 KB."}, status=400)

    sandbox = SandboxManager()
    ctx = sandbox.create(f"sample_{request.user.pk}")
    try:
        bundle, compile_error = compile_submission(language, source, ctx.root_dir)
        if bundle is None:
            return JsonResponse({"ok": False, "verdict": "CE", "error": compile_error[:8000]})
        result = run_case(
            bundle, input_data,
            time_limit=min(max(float(problem.time_limit or 1), .1), 5),
            memory_limit_mb=min(max(int(problem.memory_limit or 256), 64), 512),
        )
        return_code = int(result.get("return_code", 1))
        output = (result.get("stdout") or "")[:64_000]
        verdict = "OK" if return_code == 0 else ("TLE" if return_code == 124 else "RE")
        matches = None if expected is None or return_code != 0 else output.split() == expected.split()
        if matches is False:
            verdict = "WA"
        elif matches is True:
            verdict = "AC"
        return JsonResponse({
            "ok": return_code == 0,
            "verdict": verdict,
            "output": output,
            "expected": expected,
            "matches": matches,
            "time": round(float(result.get("time") or 0), 3),
            "error": (result.get("stderr") or "")[:8000],
        })
    finally:
        sandbox.destroy(ctx)


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
    # 🚀 Đẩy job chấm sang worker queue (không fallback local)
    # =====================================================
    try:
        dispatcher = JudgeDispatcher(redis_url=REDIS_URL)
        dispatcher.dispatch(sub.id)
    except Exception as e:
        sub.verdict = "Judge Error"
        sub.debug_info = f"Queue dispatch failed: {e}"
        sub.save(update_fields=["verdict", "debug_info"])

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
