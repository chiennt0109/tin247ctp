# contests/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Max, Exists, OuterRef
from datetime import timedelta

from .models import Contest, Participation, PracticeSession
from submissions.models import Submission
from problems.models import Problem
from datetime import timezone as dt_timezone


# ============================================================
# 🔥 PREVENT SUBMIT IN CONTEST OR PRACTICE
# ============================================================
def contest_guard(request, problem_id):
    """
    Hàm này được gọi từ submissions/views.py trước khi xử lý submission.
    - Nếu return None → tiếp tục tạo submission.
    - Nếu return HttpResponse → chặn submission (contest ended / practice ended).
    """
    problem = get_object_or_404(Problem, pk=problem_id)

    contest_id = request.GET.get("contest_id") or request.POST.get("contest_id")
    is_practice = request.GET.get("practice") or request.POST.get("practice")

    if not contest_id:
        return None

    contest = get_object_or_404(Contest, pk=contest_id)
    now = timezone.now()
     # ===============================
    # 🚫 CHẶN TRUY CẬP KHI CHƯA DIỄN RA
    # ===============================
    if now < contest.start_time:
        # Staff / superuser vẫn xem được
        if not request.user.is_staff:
            return render(request, "contests/contest_not_started.html", {
                "contest": contest
            })

    # ====================================================
    # 🔥 PRACTICE MODE — kiểm tra thời gian session
    # ====================================================
    if is_practice:
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Bạn cần đăng nhập để luyện tập.")

        session = PracticeSession.objects.filter(
            contest=contest,
            user=request.user
        ).order_by("-start_time").first()

        if not session:
            return render(request, "submissions/contest_block.html", {
                "contest": contest,
                "problem": problem,
                "error": "Bạn chưa bắt đầu PRACTICE. Hãy vào mục PRACTICE trước."
            })

        # Nếu hết giờ
        if session.remaining_seconds <= 0 or session.is_locked:
            if not session.is_locked:
                session.is_locked = True
                session.save(update_fields=["is_locked"])

            return render(request, "submissions/contest_block.html", {
                "contest": contest,
                "problem": problem,
                "error": "Phiên luyện tập đã hết giờ. Nhấn 'Làm lại từ đầu' trong PRACTICE."
            })

        return None  # → Cho phép submit trong practice

    # ====================================================
    # 🎯 CONTEST CHÍNH – chặn nếu contest đã kết thúc
    # ====================================================
    if now > contest.end_time:
        return render(request, "submissions/contest_block.html", {
            "contest": contest,
            "problem": problem,
            "error": "Cuộc thi đã kết thúc. Bạn không thể nộp bài."
        })

    return None  # Cho phép submit bình thường trong contest


# ============================================================
# LIST OF CONTESTS
# ============================================================
def contest_list(request):
    contests = Contest.objects.all().order_by("-start_time")
    now = timezone.now()
    return render(request, "contests/list.html", {
        "contests": contests,
        "now": now,
    })


# ============================================================
# CONTEST DETAIL
# ============================================================
def contest_detail(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)
    now = timezone.now()

    # 🚫 CHẶN TRUY CẬP KHI CHƯA DIỄN RA
    if now < contest.start_time:
        if not request.user.is_staff:
            return render(request, "contests/contest_not_started.html", {
                "contest": contest
            })

    # Danh sách bài
    problems = list(contest.problems.all().order_by("code"))
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    problem_letters = [letters[i] for i in range(len(problems))]
    problems_with_letters = list(zip(problem_letters, problems))

    # Xác định trạng thái
    if now > contest.end_time:
        contest_state = "ended"
    elif now < contest.start_time:
        contest_state = "not_started"
    else:
        contest_state = "running"

    return render(request, "contests/detail.html", {
        "contest": contest,
        "problems": problems,
        "problems_with_letters": problems_with_letters,
        "contest_state": contest_state,
    })



# ============================================================
# 🔥 PRACTICE MODE – PER USER TIMER (V2 FULL + CHẶN ĐỔI CONTEST)
# ============================================================


def contest_practice(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)

    # Chỉ practice khi contest đã kết thúc
    if contest.status != "finished":
        return render(request, "contests/practice.html", {
            "contest": contest,
            "error": "Contest chưa kết thúc",
            "session": None,
            "remaining": None,
        })

    # Yêu cầu login
    if not request.user.is_authenticated:
        return redirect("account_login")

    now = timezone.now()
    duration_seconds = contest.practice_time

    action = request.GET.get("action")

    # ============================================
    # 🛑 CHẶN ĐỔI SANG PRACTICE CONTEST KHÁC KHI ĐANG CÓ PHIÊN ACTIVE
    # ============================================
    active_other = PracticeSession.objects.filter(
        user=request.user,
        is_started=True,
        is_locked=False,
        cancelled=False,
    ).exclude(contest_id=contest.id).select_related("contest").first()

    if active_other:
        # Đang làm dở contest khác → bắt buộc quay lại đó
        return redirect("contests:contest_practice", contest_id=active_other.contest_id)

    # ============================================
    # 🟦 Lấy session chưa bị hủy của contest hiện tại
    # ============================================
    session = PracticeSession.objects.filter(
        contest=contest,
        user=request.user,
        cancelled=False
    ).order_by("-created_at").first()

    # ============================================
    # 🟥 CANCEL → đánh dấu cancelled + tạo session mới (chưa start)
    # ============================================
    if action == "cancel":
        if session:
            session.cancelled = True
            session.save(update_fields=["cancelled"])

        # tạo session mới (attempt ++)
        attempt = PracticeSession.objects.filter(
            contest=contest,
            user=request.user
        ).count() + 1

        session = PracticeSession.objects.create(
            contest=contest,
            user=request.user,
            attempt=attempt,
            is_started=False,
            cancelled=False,
            is_locked=False,
            start_time=None,
            end_time=None,
        )
        return redirect("contests:contest_practice", contest_id=contest.id)

    # ============================================
    # 🟩 Nếu chưa có session: tạo session mới, chưa start
    # ============================================
    if not session:
        session = PracticeSession.objects.create(
            contest=contest,
            user=request.user,
            attempt=1,
            is_started=False,
            cancelled=False,
            is_locked=False,
            start_time=None,
            end_time=None,
        )

    # ============================================
    # 🟧 Nhấn START → bắt đầu tính giờ
    # ============================================
    if action == "start" and not session.is_started:
        start = now

        session.start_time = start
        session.end_time = start + timedelta(seconds=duration_seconds)
        session.is_started = True
        session.is_locked = False
        session.save()

        return redirect("contests:contest_practice", contest_id=contest.id)

    # ============================================
    # 🟨 Session đã START → kiểm tra thời gian còn lại
    # ============================================
    if session.is_started:
        remaining = max(0, int((session.end_time - now).total_seconds()))

        # hết giờ → khóa
        if remaining <= 0 and not session.is_locked:
            session.is_locked = True
            session.save(update_fields=["is_locked"])
    else:
        remaining = None  # chưa bắt đầu

    # ============================================
    # Danh sách bài
    # ============================================
    problems = contest.problems.all().order_by("code")
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    problems_with_letters = list(zip([letters[i] for i in range(len(problems))], problems))

    return render(request, "contests/practice.html", {
        "contest": contest,
        "session": session,
        "remaining": remaining,
        "problems": problems,
        "problems_with_letters": problems_with_letters,
    })




# ============================================================
# RANKING (giữ nguyên code cũ)
# ============================================================
def contest_rank(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)

    freeze_minutes = 30
    freeze_time = contest.end_time - timedelta(minutes=freeze_minutes)
    is_frozen = freeze_time <= timezone.now() < contest.end_time

    contest_problems = list(contest.problems.all().order_by("code"))
    start_time = contest.start_time
    problem_stats = {}

    # Chỉ user có submission thuộc contest
    participants = Participation.objects.annotate(
        has_sub=Exists(
            Submission.objects.filter(
                user=OuterRef('user'),
                contest=contest
            )
        )
    ).filter(
        contest=contest,
        has_sub=True
    ).select_related("user")

    for part in participants:
        uid = part.user.id
        problem_stats[uid] = {}

        for prob in contest_problems:

            if is_frozen:
                subs = Submission.objects.filter(
                    user=part.user,
                    problem=prob,
                    contest=contest,
                    created_at__lte=freeze_time
                ).order_by("created_at")
            else:
                subs = Submission.objects.filter(
                    user=part.user,
                    problem=prob,
                    contest=contest
                ).order_by("created_at")

            tries = subs.count()

            # ------------------------
            # OI scoring
            # ------------------------
            best_score = 0
            best_sub = None

            for sub in subs:
                passed = sub.passed_tests
                total = sub.total_tests

                if total > 0:
                    score = round((passed / total) * 100)
                else:
                    score = 100 if sub.verdict == "Accepted" else 0

                if score > best_score:
                    best_score = score
                    best_sub = sub

            if best_sub and best_score > 0:
                minutes = int((best_sub.created_at - start_time).total_seconds() // 60)
                problem_stats[uid][prob.id] = {
                    "is_ac": best_score == 100,
                    "tries": tries - (1 if best_score == 100 else 0),
                    "score": best_score,
                    "time": best_sub.created_at,
                    "time_from_start": minutes,
                }
            else:
                problem_stats[uid][prob.id] = {
                    "is_ac": False,
                    "tries": tries,
                    "score": 0,
                    "time": None,
                    "time_from_start": None,
                }

        # Tổng điểm
        part.score = sum(i["score"] for i in problem_stats[uid].values())

        # Penalty
        part.penalty = sum(
            i["time_from_start"] + i["tries"] * 10
            for i in problem_stats[uid].values() if i["is_ac"]
        )

        # Lần cuối nộp
        last = Submission.objects.filter(
            created_at__range=(contest.start_time, contest.end_time),
            user=part.user,
            problem__in=contest_problems
        ).aggregate(t=Max("created_at"))["t"]

        part.last_submit = last
        part.save(update_fields=["score", "penalty", "last_submit"])

    rankings = participants.order_by("-score", "penalty", "last_submit")

    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    problem_letters = [letters[i] for i in range(len(contest_problems))]

    return render(request, "contests/rank.html", {
        "contest": contest,
        "contest_problems": contest_problems,
        "rankings": rankings,
        "problem_stats": problem_stats,
        "total_problems": len(contest_problems),
        "problem_letters": problem_letters,
        "is_frozen": is_frozen,
        "freeze_minutes": freeze_minutes,
    })


# ============================================================
# JSON RANK (giữ nguyên)
# ============================================================
def contest_rank_json(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)

    ranks = []
    for part in Participation.objects.filter(contest=contest).order_by("-score", "penalty"):
        ranks.append({
            "user": part.user.username,
            "score": part.score,
            "penalty": part.penalty,
        })

    return JsonResponse({"rankings": ranks})

def practice_rank(request, contest_id):
    contest = get_object_or_404(Contest, pk=contest_id)

    # lấy session đang practice (mới nhất của từng user)
    sessions = (
        PracticeSession.objects.filter(
            contest=contest,
            is_started=True,
            cancelled=False
        )
        .select_related("user")
        .order_by("user", "-created_at")
    )

    latest = {}
    for s in sessions:
        if s.user_id not in latest:
            latest[s.user_id] = s
    sessions = list(latest.values())

    # Danh sách bài
    problems = list(contest.problems.all().order_by("code"))
    letters = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    problems_with_letters = list(zip([letters[i] for i in range(len(problems))], problems))

    # ============================================================
    # ⭐ TÍNH ĐIỂM GIỐNG CONTEST
    # ============================================================
    problem_stats = {}       # problem_stats[user_id][problem_id] = {...}
    for sess in sessions:
        uid = sess.user_id
        problem_stats[uid] = {}
        start = sess.start_time

        for prob in problems:
            # lấy toàn bộ submission của user trong session practice này
            subs = Submission.objects.filter(
                practice_session=sess,
                problem=prob,
            ).order_by("created_at")

            tries = subs.count()

            best_score = 0
            best_sub = None

            for sub in subs:
                passed = sub.passed_tests
                total  = sub.total_tests

                if total > 0:
                    score = round((passed / total) * 100)
                else:
                    score = 100 if sub.verdict == "Accepted" else 0

                if score > best_score:
                    best_score = score
                    best_sub = sub

            if best_sub and best_score > 0:
                minutes = int((best_sub.created_at - start).total_seconds() // 60)
                problem_stats[uid][prob.id] = {
                    "is_ac": best_score == 100,
                    "score": best_score,
                    "tries": tries - (1 if best_score == 100 else 0),
                    "time_from_start": minutes,
                }
            else:
                problem_stats[uid][prob.id] = {
                    "is_ac": False,
                    "score": 0,
                    "tries": tries,
                    "time_from_start": None,
                }

        # Tổng điểm = sum(best_score mỗi bài)
        sess.total_score = sum(i["score"] for i in problem_stats[uid].values())

        # Penalty = giống contest
        sess.penalty = sum(
            i["time_from_start"] + i["tries"] * 10
            for i in problem_stats[uid].values()
            if i["is_ac"]
        )

    # ============================================================
    # ⭐ SORT GIỐNG CONTEST: Total score ↓ , penalty ↑ , last submit ↑
    # ============================================================
    sessions.sort(
        key=lambda s: (
            -s.total_score,
            s.penalty,
            s.last_submit or timezone.datetime.max.replace(tzinfo=dt_timezone.utc),
        )
    )

    # Xây AC map cho icon ✔/✘
    ac_map = {}
    for sess in sessions:
        ac_map[sess.user_id] = {}
        for prob in problems:
            ac_map[sess.user_id][prob.id] = problem_stats[sess.user_id][prob.id]["is_ac"]

    return render(request, "contests/practice_rank.html", {
        "contest": contest,
        "sessions": sessions,
        "problems_with_letters": problems_with_letters,
        "ac_map": ac_map,
        "problem_stats": problem_stats,
    })
