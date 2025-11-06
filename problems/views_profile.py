# path: problems/views_profile.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.db import connection
from submissions.models import Submission
from .models import Problem


# ===============================
# ⚙️ Kiểm tra bảng có tồn tại (tránh lỗi migrate)
# ===============================
def _table_exists(table_name: str) -> bool:
    with connection.cursor() as cursor:
        return table_name in connection.introspection.table_names()


# ===============================
# 👤 Hồ sơ người dùng
# ===============================
@login_required
def profile_view(request):
    user = request.user
    has_userprogress = _table_exists("problems_userprogress")

    # Tổng bài đã AC
    solved_qs = Submission.objects.filter(user=user, verdict="Accepted")
    solved = solved_qs.count()

    # Số bài đang làm & chưa làm
    attempted_ids = set(
        Submission.objects.filter(user=user).values_list("problem_id", flat=True)
    )
    solved_ids = set(solved_qs.values_list("problem_id", flat=True))
    in_progress = len(attempted_ids - solved_ids)
    not_started = max(0, Problem.objects.count() - len(attempted_ids))

    # Thống kê theo tag
    tags_data = {}
    for s in solved_qs.select_related("problem").prefetch_related("problem__tags"):
        for t in s.problem.tags.all():
            tags_data[t.name] = tags_data.get(t.name, 0) + 1

    # Tiến trình chi tiết (nếu có bảng)
    progresses = []
    if has_userprogress:
        from .models import UserProgress
        progresses = (
            UserProgress.objects.filter(user=user)
            .select_related("problem")
            .order_by("-last_submit")
        )

    return render(
        request,
        "users/profile.html",
        {
            "user": user,
            "progresses": progresses,
            "solved": solved,
            "in_progress": in_progress,
            "not_started": not_started,
            "tags_data": tags_data,
            "has_userprogress": has_userprogress,
        },
    )


# ===============================
# 🔒 Đổi mật khẩu
# ===============================
@login_required
def change_password_view(request):
    """
    Trang đổi mật khẩu thân thiện, có thông báo và giữ session.
    """
    user = request.user

    if request.method == "POST":
        form = PasswordChangeForm(user, request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "✅ Mật khẩu đã được cập nhật thành công!")
            # ⚙️ Sửa redirect đúng namespace
            return redirect("/problems/profile/")
        else:
            messages.error(request, "⚠️ Có lỗi xảy ra, vui lòng kiểm tra lại.")
    else:
        form = PasswordChangeForm(user)

    return render(
        request,
        "users/change_password.html",
        {"form": form, "title": "Đổi mật khẩu"},
    )
