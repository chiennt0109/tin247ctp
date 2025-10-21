from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from problems.models import Problem
from .models import Submission
from judge.grader import grade_submission


@login_required
def submit(request, problem_id):
    """Trang nộp bài cho 1 problem"""
    problem = get_object_or_404(Problem, id=problem_id)
    ctx = {'problem': problem, 'result': None}

    if request.method == 'POST':
        lang = request.POST.get('language')
        code = request.POST.get('source')

        if not lang or not code:
            ctx['error'] = "Vui lòng chọn ngôn ngữ và nhập mã nguồn!"
            return render(request, 'submissions/submit.html', ctx)

        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=lang,
            source_code=code
        )

        # Gọi hàm chấm bài
        verdict, exec_time, passed, failed = grade_submission(sub)

        sub.verdict = verdict
        sub.exec_time = exec_time
        sub.save()

        ctx.update({
            'result': sub,
            'passed': passed,
            'failed': failed
        })

        return render(request, 'submissions/result.html', ctx)

    return render(request, 'submissions/submit.html', ctx)


@login_required
def my_submissions(request):
    """Liệt kê các submission của user"""
    subs = Submission.objects.filter(user=request.user).select_related('problem').order_by('-created_at')
    return render(request, 'submissions/result.html', {'subs': subs})
