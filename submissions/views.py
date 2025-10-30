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
        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=request.POST.get("language"),
            source_code=request.POST.get("source"),
            verdict="Pending"
        )

        verdict, time_used, passed, total, debug = grade_submission(sub)

        sub.verdict = verdict
        sub.exec_time = time_used
        sub.passed_tests = passed
        sub.total_tests = total
        sub.debug_info = debug
        sub.save()

        return redirect("submission_detail", submission_id=sub.id)

    return render(request, "submissions/submit.html", {"problem": problem})

@login_required
def submission_detail(request, submission_id):
    sub = get_object_or_404(Submission, pk=submission_id)
    return render(request, "submissions/detail.html", {"sub": sub})
