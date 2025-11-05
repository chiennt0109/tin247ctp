from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Submission
from problems.models import Problem
from judge.grader import grade_submission
from contests.utils import update_participation

@login_required
def submission_create(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)

    if request.method == "POST":
        lang = request.POST.get("language")
        code = request.POST.get("source")

        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=lang,
            source_code=code,
            verdict="Pending"
        )

        # ✅ Gọi grader (định dạng mới)
        verdict, exec_time, passed, total, debug = grade_submission(sub)

        # ✅ Lưu kết quả
        sub.verdict = verdict
        sub.exec_time = float(exec_time)
        sub.passed_tests = passed
        sub.total_tests = total
        sub.debug_info = str(debug)
        sub.save()
        # cap nhat contest
        update_participation(request.user, sub.problem)
        contest = Contest.objects.filter(problems=sub.problem).first()
        if contest:
            return redirect("contest_rank", contest_id=contest.id)
        else:
            return redirect("submission_detail", submission_id=sub.id)

    return render(request, "submissions/submit.html", {"problem": problem})

@login_required
def submission_detail(request, submission_id):
    sub = get_object_or_404(Submission, id=submission_id)
    return render(request, "submissions/result.html", {
        "result": sub,
        "problem": sub.problem,
        "submissions": Submission.objects.filter(
            user=request.user, problem=sub.problem
        ).order_by("-created_at")
    })

def my_submissions(request):
    subs = Submission.objects.filter(user=request.user).order_by("-id")
    return render(request, "submissions/my_submissions.html", {"submissions": subs})
