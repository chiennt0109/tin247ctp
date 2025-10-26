# path: submissions/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from problems.models import Problem
from .models import Submission
from judge.grader import grade_submission

@login_required
def submit(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    ctx = {'problem': problem, 'result': None}

    if request.method == 'POST':
        lang = request.POST.get('language')
        code = request.POST.get('source')

        if not lang or not code:
            ctx['error'] = "Bạn cần chọn ngôn ngữ và nhập mã nguồn!"
            return render(request, 'submissions/submit.html', ctx)

        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=lang,
            source_code=code
        )

        # Chấm bài
        verdict, exec_time, passed, total = grade_submission(sub)
        sub.verdict = verdict
        sub.exec_time = exec_time
        sub.passed_tests = passed
        sub.total_tests = total
        sub.save()

        # Cập nhật thống kê Problem
        problem.submission_count += 1
        if verdict == 'Accepted':
            problem.ac_count += 1
        problem.save()

        ctx['result'] = sub
        ctx['submissions'] = Submission.objects.filter(user=request.user, problem=problem).order_by('-created_at')
        return render(request, 'submissions/result.html', ctx)

    return render(request, 'submissions/submit.html', ctx)


@login_required
def my_submissions(request):
    subs = Submission.objects.filter(user=request.user).select_related('problem').order_by('-created_at')
    return render(request, 'submissions/result.html', {'submissions': subs})
