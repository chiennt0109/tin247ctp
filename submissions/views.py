from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Submission
from problems.models import Problem
from judge.grader import grade_submission

@login_required
def submission_create(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)

    if request.method == "POST":
        language = request.POST.get("language")
        code = request.POST.get("source")

        # Tạo submission
        sub = Submission.objects.create(
            user=request.user,
            problem=problem,
            language=language,
            source_code=code,
            verdict="Pending"
        )

        # Chấm + nhận logs
        # ✅ Parse result (with debug list)
        if isinstance(result, tuple):
            if len(result) == 5:
                verdict, exec_time, passed, total, debug_info = result
            else:
                verdict = str(result[0])
                exec_time, passed, total, debug_info = 0.0, 0, 0, []
        else:
            verdict = str(result)
            exec_time, passed, total, debug_info = 0.0, 0, 0, []
        
        # ✅ Save
        sub.verdict = verdict
        sub.exec_time = exec_time
        sub.passed_tests = passed
        sub.total_tests = total
        sub.debug_info = str(debug_info)[:5000]  # tránh quá dài
        sub.save()
        
        return redirect("submission_detail", submission_id=sub.id)


        # Chuẩn hóa kết quả (v, time, passed, total, logs)
        verdict, exec_time, passed, total, logs = None, 0.0, 0, 0, []
        if isinstance(result, tuple):
            # hỗ trợ các phiên bản khác nhau
            if len(result) >= 4:
                verdict, exec_time, passed, total = result[:4]
                if len(result) >= 5:
                    logs = result[4] or []
            else:
                verdict = str(result[0])
        else:
            verdict = str(result)

        # Lưu submission
        sub.verdict = verdict
        sub.exec_time = exec_time
        sub.passed_tests = passed
        sub.total_tests = total
        sub.save()

        # Hiển thị luôn trang chi tiết với logs (không cần migration DB)
        return render(request, "submissions/detail.html", {"sub": sub, "logs": logs})

    return render(request, "submissions/submit.html", {"problem": problem})

@login_required
def submission_detail(request, submission_id):
    sub = get_object_or_404(Submission, pk=submission_id)
    # Trang này có thể được vào từ redirect cũ, khi đó không có logs runtime
    return render(request, "submissions/detail.html", {"sub": sub, "logs": []})

@login_required
def my_submissions(request):
    subs = Submission.objects.filter(user=request.user).order_by("-created_at")
    return render(request, "submissions/my_submissions.html", {"subs": subs})
