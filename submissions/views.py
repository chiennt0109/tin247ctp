# path: submissions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Submission
from problems.models import Problem
from judge.grader import grade_submission
from contests.utils import update_participation
from contests.models import Contest


@login_required
def submission_create(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)
    contest_id = request.GET.get("contest_id") or request.POST.get("contest_id")

    if request.method == "POST":
        lang = request.POST.get("language")
        code = request.POST.get("source")

        # ✅ Tạo submission mới
        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=lang,
            source_code=code,
            verdict="Pending"
        )

        # ✅ Chấm tự động
        verdict, exec_time, passed, total, debug = grade_submission(sub)
        sub.verdict = verdict
        sub.exec_time = float(exec_time)
        sub.passed_tests = passed
        sub.total_tests = total
        sub.debug_info = str(debug)
        sub.save()

        # ✅ Cập nhật bảng điểm contest (nếu có)
        update_participation(request.user, sub.problem)

        # ✅ Điều hướng hợp lý
        if contest_id:
            # Có contest: quay lại kết quả + tham chiếu contest_id
            return redirect(f"/submissions/{sub.id}/?contest_id={contest_id}")
        else:
            # Nếu problem thuộc contest nào đó → tự gán contest_id
            contest = Contest.objects.filter(problems=sub.problem).first()
            if contest:
                return redirect(f"/submissions/{sub.id}/?contest_id={contest.id}")
            # Ngược lại: chỉ hiển thị kết quả bình thường
            return redirect("submissions:submission_detail", submission_id=sub.id)

    return render(
        request,
        "submissions/submit.html",
        {"problem": problem, "contest_id": contest_id},
    )


@login_required
def submission_detail(request, submission_id):
    sub = get_object_or_404(Submission, id=submission_id)
    contest_id = request.GET.get("contest_id")

    return render(
        request,
        "submissions/result.html",
        {
            "result": sub,
            "problem": sub.problem,
            "contest_id": contest_id,
            "submissions": Submission.objects.filter(
                user=request.user, problem=sub.problem
            ).order_by("-created_at"),
        },
    )


@login_required
def my_submissions(request):
    subs = Submission.objects.filter(user=request.user).order_by("-id")
    return render(request, "submissions/my_submissions.html", {"submissions": subs})
