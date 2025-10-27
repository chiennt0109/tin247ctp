# path: problems/admin.py
import os, zipfile, tempfile
from django import forms
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils.html import format_html
from .models import Problem, TestCase, Tag


# ===========================
# 📦 FORM UPLOAD ZIP
# ===========================
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


# ===========================
# 🧠 RULE-BASED AI TAGGER
# ===========================
def ai_tag_suggest(text: str):
    """Trích xuất tag theo heuristic rule — miễn phí và cực nhanh."""
    t = (text or "").lower()
    tags = []
    if any(k in t for k in ["đồ thị", "graph", "đỉnh", "cạnh"]):
        tags.append("Graph")
    if any(k in t for k in ["bfs", "dfs", "dijkstra", "shortest path", "đường đi ngắn nhất"]):
        tags.append("Shortest Path")
    if any(k in t for k in ["quy hoạch động", "dynamic programming", "dp", "f[i]"]):
        tags.append("DP")
    if any(k in t for k in ["chuỗi", "string", "prefix", "suffix", "substring", "kmp", "z-algorithm"]):
        tags.append("String")
    if any(k in t for k in ["tham lam", "greedy"]):
        tags.append("Greedy")
    if any(k in t for k in ["hai con trỏ", "two pointers"]):
        tags.append("Two Pointers")
    if any(k in t for k in ["cây phân đoạn", "segment tree", "fenwick", "binary indexed tree"]):
        tags.append("Data Structure")
    if any(k in t for k in ["mod", "modulo", "ước", "bội", "gcd", "lcm", "prime"]):
        tags.append("Math")
    if not tags:
        tags.append("General")
    # loại trùng, giữ thứ tự
    return list(dict.fromkeys(tags))


def apply_tags_to_problem(problem):
    """Tạo và gán tag vào Problem"""
    tags = ai_tag_suggest(problem.statement)
    tag_objs = []
    for name in tags:
        tag, _ = Tag.objects.get_or_create(
            name=name,
            defaults={"slug": name.lower().replace(" ", "-")}
        )
        tag_objs.append(tag)
    problem.tags.set(tag_objs)
    return tags


# ===========================
# ⚙️ ADMIN CHÍNH
# ===========================
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "difficulty", "ac_count", "submission_count", "view_tests_link")
    search_fields = ("code", "title")
    change_form_template = "admin/problems/change_form_with_upload.html"
    filter_horizontal = ("tags",)
    readonly_fields = ("created_at",)

    # -------------------------
    # Giao diện “Change Form”
    # -------------------------
    def change_view(self, request, object_id, form_url="", extra_context=None):
        problem = Problem.objects.get(pk=object_id)
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        extra_context["auto_tag_url"] = reverse("admin:auto_tag_problem", args=[problem.id])
        return super().change_view(request, object_id, form_url, extra_context)

    # -------------------------
    # Gợi ý tag bằng API (ajax)
    # -------------------------
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
            path("<int:problem_id>/view_tests/", self.admin_site.admin_view(self.view_tests), name="view_tests"),
            path("<int:problem_id>/auto_tag/", self.admin_site.admin_view(self.auto_tag), name="auto_tag_problem"),
            path("<int:test_id>/delete_test/", self.admin_site.admin_view(self.delete_test), name="delete_test"),
        ]
        return custom + urls

    # -------------------------
    # Xử lý gợi ý tag AI
    # -------------------------
    def auto_tag(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tags = apply_tags_to_problem(problem)
        messages.success(request, f"🤖 Đã tự động gán {len(tags)} tag: {', '.join(tags)}")
        return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

    # -------------------------
    # Upload Test
    # -------------------------
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
                    with zipfile.ZipFile(zip_path, "r") as z:
                        z.extractall(tmpdir)
                    for root, _, files in os.walk(tmpdir):
                        for fn in files:
                            if not fn.endswith((".in", ".inp", ".txt")):
                                continue
                            name, _ = os.path.splitext(fn)
                            inp_path = os.path.join(root, fn)
                            out_candidates = [name + ".out", name + ".ans", name + ".txt"]
                            out_path = None
                            for c in out_candidates:
                                if os.path.exists(os.path.join(root, c)):
                                    out_path = os.path.join(root, c)
                                    break
                            if not out_path:
                                skipped += 1
                                continue
                            with open(inp_path, encoding="utf-8", errors="ignore") as fi:
                                inp_data = fi.read().strip()
                            with open(out_path, encoding="utf-8", errors="ignore") as fo:
                                out_data = fo.read().strip()
                            TestCase.objects.create(problem=problem, input_data=inp_data, expected_output=out_data)
                            imported += 1
                messages.success(request, f"✅ Đã import {imported} test case (bỏ qua {skipped}).")
                return redirect(reverse("admin:problems_problem_change", args=[problem.id]))
        else:
            form = UploadTestZipForm()
        return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    # -------------------------
    # View test + xóa test
    # -------------------------
    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {"problem": problem, "testcases": tests})

    def delete_test(self, request, test_id):
        try:
            t = TestCase.objects.get(pk=test_id)
            t.delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error", "msg": "Not found"}, status=404)

    # -------------------------
    # Liên kết xem test
    # -------------------------
    def view_tests_link(self, obj):
        url = reverse("admin:view_tests", args=[obj.id])
        return format_html('<a href="{}" class="button" target="_blank">👁 Xem test</a>', url)
    view_tests_link.short_description = "Test cases"
