# path: submissions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Submission
from problems.models import Problem
from judge.grader import grade_submission   # ✅ dùng grader chính


@login_required
def submission_create(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)

    if request.method == "POST":
        language = request.POST.get("language")
        code = request.POST.get("source")

        # ✅ Tạo submission DB trước
        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=language,
            source_code=code,
            verdict="Pending"
        )

        # ✅ Gọi grader
        result = grade_submission(sub)

        # ✅ Hệ thống cũ trả về 4 giá trị (v, time, passed, total)
        # ✅ Hệ thống mới có thể trả về 2 hoặc 1 giá trị
        if isinstance(result, tuple):
            if len(result) == 4:
                verdict, exec_time, passed, total = result
            elif len(result) == 2:
                verdict, err = result
                exec_time, passed, total = 0.0, 0, 0
            else:
                verdict = str(result[0])
                exec_time, passed, total = 0.0, 0, 0
        else:
            verdict = str(result)
            exec_time, passed, total = 0.0, 0, 0

        # ✅ Cập nhật Submission
        sub.verdict = verdict
        sub.exec_time = exec_time
        sub.passed_tests = passed
        sub.total_tests = total
        sub.save()

        return redirect("submission_detail", submission_id=sub.id)

    return render(request, "submissions/submit.html", {
        "problem": problem
    })


@login_required
def submission_detail(request, submission_id):
    sub = get_object_or_404(Submission, pk=submission_id)
    return render(request, "submissions/detail.html", {"sub": sub})

def my_submissions(request):
    subs = Submission.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "submissions/my_submissions.html", {"subs": subs})
