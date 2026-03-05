# contests/admin.py
from django.contrib import admin
from django.shortcuts import redirect, render
from django import forms

from . import models
from .models import ContestEditorialAccess
from problems.models import Problem

Contest = models.Contest
Participation = models.Participation
PracticeSession = models.PracticeSession


# ============================================================
# 1) BULK FORM: Chọn contest + mode → áp cho tất cả problems
# ============================================================

class BulkContestEditorialForm(forms.Form):
    contest = forms.ModelChoiceField(
        queryset=Contest.objects.all(),
        label="Contest",
        required=True
    )
    mode = forms.ChoiceField(
        choices=ContestEditorialAccess.MODE_CHOICES,
        label="Rule áp dụng",
        required=True
    )


# ============================================================
# 2) ADMIN CHO BULK APPLY RULE (KHÔNG XOÁ CHỨC NĂNG OLD)
# ============================================================

@admin.register(ContestEditorialAccess)
class ContestEditorialAccessAdmin(admin.ModelAdmin):

    list_display = ("contest", "problem", "mode")
    list_filter = (
        "mode",
        ("contest", admin.RelatedOnlyFieldListFilter),
        ("problem", admin.RelatedOnlyFieldListFilter),
    )
    search_fields = (
        "contest__name",
        "problem__code",
        "problem__title",
    )
    ordering = ("-contest__start_time", "problem__code")

    # sử dụng template tùy chỉnh cho trang add
    add_form = BulkContestEditorialForm
    add_form_template = "admin/contest_editorial_bulk_add.html"

    fieldsets = (
        ("Thiết lập quyền xem lời giải cho contest", {
            "fields": ("contest", "problem", "mode"),
            "description": (
                "<b>Giải thích mode:</b><br>"
                "- <b>Hide during contest</b>: Cấm hoàn toàn trong contest.<br>"
                "- <b>Show after contest ends</b>: Chỉ hiển thị sau khi contest kết thúc.<br>"
                "- <b>Show free editorial</b>: Chỉ hiển thị nếu bài là free.<br>"
                "- <b>Paid only</b>: Chỉ hiển thị nếu user đã mua lời giải.<br>"
            )
        }),
    )

    # OVERRIDE TRANG ADD → CHO PHÉP APPLY TẤT CẢ BÀI
    def add_view(self, request, form_url="", extra_context=None):
        """
        Nếu POST → apply rule cho tất cả problems trong contest
        Nếu GET → hiển thị form bulk
        """
        if request.method == "POST":
            form = BulkContestEditorialForm(request.POST)
            if form.is_valid():
                contest = form.cleaned_data["contest"]
                mode = form.cleaned_data["mode"]

                problems = contest.problems.all()

                # Xóa rule cũ của contest
                ContestEditorialAccess.objects.filter(contest=contest).delete()

                # Tạo rule mới
                ContestEditorialAccess.objects.bulk_create([
                    ContestEditorialAccess(contest=contest, problem=p, mode=mode)
                    for p in problems
                ])

                self.message_user(
                    request,
                    f"Đã áp dụng rule '{mode}' cho {len(problems)} bài trong contest '{contest.name}'."
                )
                return redirect("admin:contests_contesteditorialaccess_changelist")

        else:
            form = BulkContestEditorialForm()

        context = {"form": form}
        return render(request, "admin/contest_editorial_bulk_add.html", context)


# ============================================================
# 3) CONTEST ADMIN – vẫn tạo contest mới bình thường
# ============================================================

@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time", "practice_time", "practice_open")
    list_editable = ("practice_time", "practice_open")
    search_fields = ("name",)

    fieldsets = (
        ("Thông tin contest", {
            "fields": ("name", "description", "start_time", "end_time", "problems", "is_public")
        }),
        ("Practice mode", {
            "fields": ("practice_time", "practice_open"),
            "description": "Giáo viên có thể thay đổi thời gian PRACTICE bất kỳ lúc nào."
        }),
        ("Editorial rule (auto)", {
            "description": (
                "Danh sách rule của từng bài trong contest. "
                "Bạn có thể sửa từng rule hoặc dùng chức năng Apply All."
            ),
            "fields": ()
        }),
    )

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get("original")

        if obj:
            rules = ContestEditorialAccess.objects.filter(contest=obj)
            html = "<ul>"
            for r in rules:
                html += (
                    f"<li><b>{r.problem.code}</b>: {r.get_mode_display()} "
                    f"<a href='/admin/contests/contesteditorialaccess/{r.id}/change/'>✍</a>"
                    "</li>"
                )
            html += "</ul>"

            # thêm help_text vào trường problems
            context["adminform"].form.fields["problems"].help_text = (
                "Danh sách rule áp dụng tự động:<br>" + html +
                "<br><a class='button' href='/admin/contests/contesteditorialaccess/add/'>"
                "⚙️ Apply rule to ALL problems</a>"
            )

        return super().render_change_form(request, context, *args, **kwargs)


# ============================================================
# 4) Participation admin
# ============================================================

@admin.register(Participation)
class ParticipationAdmin(admin.ModelAdmin):
    list_display = ("contest", "user", "score", "penalty", "last_submit")
    list_filter = ("contest",)
    search_fields = ("user__username",)


# ============================================================
# 5) PracticeSession admin
# ============================================================

@admin.register(PracticeSession)
class PracticeSessionAdmin(admin.ModelAdmin):
    list_display = (
        "contest",
        "user",
        "attempt",
        "is_started",
        "is_locked",
        "cancelled",
        "score",
        "last_submit",
    )
    list_filter = ("contest", "is_started", "is_locked", "cancelled")
    search_fields = ("user__username",)
