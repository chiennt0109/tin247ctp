# contests/admin.py
from django.contrib import admin as django_admin
from django.shortcuts import redirect, render
from django import forms
from django.db.models import Case, IntegerField, Value, When

from . import models
from .models import ContestEditorialAccess, ContestProblemOrder
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


class ContestAdminForm(forms.ModelForm):
    """Make selecting problems in the contest admin quick and explicit."""

    class Meta:
        model = Contest
        fields = "__all__"
        help_texts = {
            "problems": (
                "Tìm nhanh theo mã hoặc tên bài, sau đó dùng các nút mũi tên "
                "để thêm hoặc bớt bài. Bài sẽ hiển thị trong contest đúng theo "
                "thứ tự ở cửa sổ Chosen problems; có thể bớt rồi thêm lại để "
                "đưa một bài xuống cuối."
            ),
            "allowed_users": (
                "Để trống để mọi tài khoản nhìn thấy contest. Nếu chọn ít nhất "
                "một tài khoản, contest chỉ hiển thị cho các tài khoản đã chọn."
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            return
        positions = self.instance.problem_display_orders.values_list(
            "problem_id", "position"
        )
        ordering = Case(
            *(When(pk=problem_id, then=Value(position)) for problem_id, position in positions),
            default=Value(1_000_000),
            output_field=IntegerField(),
        )
        self.fields["problems"].queryset = Problem.objects.annotate(
            contest_position=ordering
        ).order_by("contest_position", "code")


# ============================================================
# 2) ADMIN CHO BULK APPLY RULE (KHÔNG XOÁ CHỨC NĂNG OLD)
# ============================================================

@django_admin.register(ContestEditorialAccess)
class ContestEditorialAccessAdmin(django_admin.ModelAdmin):

    list_display = ("contest", "problem", "mode")
    list_filter = (
        "mode",
        ("contest", django_admin.RelatedOnlyFieldListFilter),
        ("problem", django_admin.RelatedOnlyFieldListFilter),
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

@django_admin.register(Contest)
class ContestAdmin(django_admin.ModelAdmin):
    form = ContestAdminForm
    filter_horizontal = ("problems", "allowed_users")
    list_display = ("name", "start_time", "end_time", "practice_time", "practice_open")
    list_editable = ("practice_time", "practice_open")
    search_fields = ("name",)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        selected_ids = {
            str(pk)
            for pk in form.cleaned_data["problems"].values_list("pk", flat=True)
        }
        ordered_ids = [
            int(pk) for pk in request.POST.getlist("problems") if pk in selected_ids
        ]
        ContestProblemOrder.objects.filter(contest=form.instance).delete()
        ContestProblemOrder.objects.bulk_create(
            ContestProblemOrder(
                contest=form.instance,
                problem_id=problem_id,
                position=position,
            )
            for position, problem_id in enumerate(ordered_ids, start=1)
        )

    fieldsets = (
        ("Thông tin contest", {
            "fields": ("name", "description", "start_time", "end_time", "problems", "is_public")
        }),
        ("Tài khoản được phép nhìn thấy", {
            "fields": ("allowed_users",),
            "description": (
                "Mặc định để trống: mọi tài khoản đều nhìn thấy. "
                "Khi thêm tài khoản: chỉ các tài khoản trong cửa sổ bên phải "
                "mới nhìn thấy contest."
            ),
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

@django_admin.register(Participation)
class ParticipationAdmin(django_admin.ModelAdmin):
    list_display = ("contest", "user", "score", "penalty", "last_submit")
    list_filter = ("contest",)
    search_fields = ("user__username",)


# ============================================================
# 5) PracticeSession admin
# ============================================================

@django_admin.register(PracticeSession)
class PracticeSessionAdmin(django_admin.ModelAdmin):
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
