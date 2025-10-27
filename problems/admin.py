# path: problems/admin.py
import os, zipfile, tempfile
from django import forms
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.utils.html import format_html
from .models import Problem, TestCase, Tag

# -------------------------------------------
# 🧩 FORM UPLOAD TEST ZIP
# -------------------------------------------
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")

# -------------------------------------------
# 🧠 AI AUTO TAG HELPER
# -------------------------------------------
def auto_tag_problem(problem):
    """
    Hàm hỗ trợ: dựa trên nội dung statement,
    gợi ý và gán tag tự động cho Problem (rule-based miễn phí)
    """
    text = (problem.statement or "").lower()
    suggested = []

    if any(k in text for k in ["đồ thị", "graph", "cạnh", "đỉnh"]):
        suggested.append("Graph")
    if any(k in text for k in ["bfs", "dfs", "dijkstra", "đường đi ngắn nhất", "shortest path"]):
        suggested.append("Shortest Path")
    if any(k in text for k in ["quy hoạch động", "dynamic programming", "dp", "f[i]"]):
        suggested.append("DP")
    if any(k in text for k in ["chuỗi", "string", "substring", "prefix", "kmp", "z-algorithm"]):
        suggested.append("String")
    if any(k in text for k in ["tham lam", "greedy"]):
        suggested.append("Greedy")
    if any(k in text for k in ["hai con trỏ", "two pointers", "two pointer"]):
        suggested.append("Two Pointers")
    if any(k in text for k in ["sort", "sắp xếp"]):
        suggested.append("Sorting")
    if any(k in text for k in ["mod", "modulo", "ước", "bội", "gcd", "lcm", "prime"]):
        suggested.append("Math")
    if not suggested:
        suggested.append("General")

    # loại trùng và sắp xếp
    suggested = list(dict.fromkeys(suggested))

    # tạo tag nếu chưa tồn tại
    tag_objs = []
    for name in suggested:
        tag, _ = Tag.objects.get_or_create(
            name=name,
            defaults={"slug": name.lower().replace(" ", "-")}
        )
        tag_objs.append(tag)

    # gán vào problem
    problem.tags.set(tag_objs)
    return suggested

# -------------------------------------------
# 🧱 CLASS ADMIN CHÍNH
# -------------------------------------------
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = (
        "code", "title", "difficulty",
        "time_limit", "memory_limit", "view_tests_link"
    )
    search_fields = ("code", "title")
    change_form_template = "admin/problems/change_form_with_upload.html"
    filter_horizontal = ("tags",)  # ✅ đảm bảo hiển thị danh sách tag

    # -------------------------------------
    # Mở form change có thêm context
    # -------------------------------------
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    # -------------------------------------
    # Link xem test
    # -------------------------------------
    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">👁 Xem test</a>',
            reverse("admin:view_tests", args=[obj.id])
        )
    view_tests_link.short_description = "Test cases"

    # -------------------------------------
    # URL bổ sung
    # -------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("<int:problem_id>/upload_tests/",
                 self.admin_site.admin_view(self.upload_tests),
                 name="upload_tests"),
            path("<int:problem_id>/view_tests/",
                 self.admin_site.admin_view(self.view_tests),
                 name="view_tests"),
            path("<int:problem_id>/auto_tag/",
                 self.admin_site.admin_view(self.auto_tag_view),
                 name="auto_tag"),  # ✅ endpoint AI tag ngay trong admin
        ]
        return my_urls + urls

    # -------------------------------------
    # Tính năng AI Tag thủ công (qua nút)
    # -------------------------------------
    def auto_tag_view(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tags = auto_tag_problem(problem)
        messages.success(
            request, f"🤖 Đã tự động gợi ý và gán {len(tags)} tag: {', '.join(tags)}"
        )
        return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

    # -------------------------------------
    # Upload ZIP
    # -------------------------------------
    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        if request.method == "POST":
            form = UploadTestZipForm(request.POST, request.FILES)
            if form.is_valid():
                zip_file = request.FILES["zip_file"]
                imported, skipped = 0, 0
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, "tests.zip")
                    with open(zip_path, "wb") as f:
                        for chunk in zip_file.chunks():
                            f.write(chunk)
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(tmpdir)
                    for root, _, files in os.walk(tmpdir):
                        for filename in files:
                            name, ext = os.path.splitext(filename)
                            if ext.lower() not in [".in", ".inp", ".txt"]:
                                continue
                            inp_path = os.path.join(root, filename)
                            out_path = None
                            out_candidates = [
                                name + ".out", name + ".ans", name + ".txt",
                                filename.replace(".inp", ".out"),
                                filename.replace(".in", ".out")
                            ]
                            parent_dir = os.path.basename(root)
                            maybe_out = os.path.join(root, parent_dir + ".out")
                            if os.path.exists(maybe_out):
                                out_path = maybe_out
                            else:
                                for cand in out_candidates:
                                    if os.path.exists(os.path.join(root, cand)):
                                        out_path = os.path.join(root, cand)
                                        break
                            if not out_path:
                                skipped += 1
                                continue
                            try:
                                with open(inp_path, encoding="utf-8", errors="ignore") as fi:
                                    inp_data = fi.read().strip()
                                with open(out_path, encoding="utf-8", errors="ignore") as fo:
                                    out_data = fo.read().strip()
                                TestCase.objects.create(
                                    problem=problem,
                                    input_data=inp_data,
                                    expected_output=out_data
                                )
                                imported += 1
                            except Exception as e:
                                print(f"❌ Lỗi đọc {inp_path}: {e}")
                                skipped += 1

                messages.success(
                    request,
                    f"✅ Đã import {imported} test case cho {problem.code} (bỏ qua {skipped})."
                )
                return redirect(reverse("admin:problems_problem_change", args=[problem.id]))
        else:
            form = UploadTestZipForm()
        return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    # -------------------------------------
    # View test
    # -------------------------------------
    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        testcases = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {
            "problem": problem,
            "testcases": testcases,
        })
