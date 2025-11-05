# path: problems/views_profile.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from .models import UserProgress

@login_required
def profile_view(request):
    user = request.user
    progresses = UserProgress.objects.filter(user=user).select_related("problem")
    solved = progresses.filter(status="solved").count()
    in_progress = progresses.filter(status="in_progress").count()
    not_started = progresses.filter(status="not_started").count()

    tags_data = {}
    for p in progresses.filter(status="solved"):
        for t in p.problem.tags.all():
            tags_data[t.name] = tags_data.get(t.name, 0) + 1

    return render(request, "users/profile.html", {
        "user": user,
        "progresses": progresses,
        "solved": solved,
        "in_progress": in_progress,
        "not_started": not_started,
        "tags_data": tags_data,
    })

@login_required
def change_password_view(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "✅ Mật khẩu đã được thay đổi thành công!")
            return redirect("profile")
        else:
            messages.error(request, "❌ Có lỗi xảy ra. Vui lòng thử lại.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "users/change_password.html", {"form": form})
