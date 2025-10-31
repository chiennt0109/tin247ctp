# path: submissions/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Submission
from problems.models import Problem
from judge.grader import grade_submission

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

        result = grade_submission(sub)

        if isinstance(result, tuple):
            verdict, t, p, tot, debug = result
        else:
            verdict, t, p, tot, debug = result, 0, 0, 0, {}

        sub.verdict = verdict
        sub.exec_time = float(t)
        sub.passed_tests = p
        sub.total_tests = tot
        sub.debug_info = str(debug)
        sub.save()

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

