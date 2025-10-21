from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from problems.models import Problem
from .models import Submission
from judge.grader import grade_submission
import traceback

@login_required
def submit(request, problem_id):
    problem = get_object_or_404(Problem, id=problem_id)
    ctx = { 'problem': problem, 'result': None }

    if request.method == 'POST':
        try:
            lang = request.POST.get('language')
            code = request.POST.get('source')
            sub = Submission.objects.create(
                user=request.user,
                problem=problem,
                language=lang,
                source_code=code
            )

            verdict, exec_time = grade_submission(sub)
            sub.verdict = verdict
            sub.exec_time = exec_time
            sub.save()

            ctx['result'] = sub
            return render(request, 'submissions/result.html', ctx)

        except Exception as e:
            print("❌ Error in submit():", e)
            traceback.print_exc()
            ctx['error'] = str(e)
            return render(request, 'submissions/submit.html', ctx)

    return render(request, 'submissions/submit.html', ctx)


@login_required
def my_submissions(request):
    try:
        subs = Submission.objects.filter(user=request.user).select_related('problem').order_by('-created_at')
        return render(request, 'submissions/result.html', { 'subs': subs })
    except Exception as e:
        print("❌ Error in my_submissions():", e)
        traceback.print_exc()
        return render(request, 'submissions/result.html', { 'error': str(e) })
