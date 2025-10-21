from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from problems.models import Problem
from .models import Submission
from judge.grader import grade_submission

@login_required
def submit(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    ctx = { 'problem': problem, 'result': None }
    if request.method == 'POST':
        lang = request.POST.get('language')
        code = request.POST.get('source')
        sub = Submission.objects.create(user=request.user, problem=problem, language=lang, source_code=code)
        verdict, exec_time = grade_submission(sub)
        sub.verdict = verdict
        sub.exec_time = exec_time
        sub.save()
        ctx['result'] = sub
        return render(request, 'submissions/result.html', ctx)
    return render(request, 'submissions/submit.html', ctx)

@login_required
def my_submissions(request):
    subs = Submission.objects.filter(user=request.user).select_related('problem').order_by('-created_at')
    return render(request, 'submissions/result.html', { 'subs': subs })
