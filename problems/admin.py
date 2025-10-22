# /opt/render/project/src/problems/admin.py
import os
import zipfile
import tempfile

from django import forms
from django.contrib import admin, messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import path, reverse

from .models import Problem, TestCase


# ============================================================
# 🧩 FORM: Upload file ZIP chứa các test case (.inp/.out)
# ============================================================
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


# ============================================================
# 🧩 INLINE: Cho phép thêm test case thủ công trong trang Problem
# ============================================================
class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1
    fields = ("input_data", "expected_output")
    verbose_name = "Test case"
    verbose_name_plural = "Danh sách test case"


# ============================================================
# 🧩 ADMIN: Giao diện quản lý Problem + upload ZIP + AJAX test list
# ============================================================
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "time_limit", "memory_limit")
    search_fields = ("code", "title")
    inlines = [TestCaseInline]

    # Template override để thêm nút Upload + vùng AJAX test cases
    change_form_template = "admin/problems/change_form_with_upload.html"

    # -------------------------------
    # URL con dưới /admin/problems/problem/<id>/
    # -------------------------------
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:problem_id>/upload_tests/",
                self.admin_site.admin_view(self.upload_tests),
                name="upload_tests",
            ),
            path(
                "<int:problem_id>/load_tests/",
                self.admin_site.admin_view(self.load_tests),
                name="load_tests",
            ),
        ]
        return my_urls + urls

    # -------------------------------
    # Truyền biến vào template
    # -------------------------------
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    # -------------------------------
    # ⚙️ Upload ZIP testcases
    # -------------------------------
    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)

        if request.method == "POST":
            form = UploadTestZipForm(request.POST, request.FILES)
            if form.is_valid():
                zip_file = request.FILES["zip_file"]
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, "tests.zip")
                    with open(zip_path, "wb") as f:
                        for chunk in zip_file.chunks():
                            f.write(chunk)

                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(tmpdir)

                    imported = 0
                    skipped = 0
                    for root, _, files in os.walk(tmpdir):
                        for filename in files:
                            name, ext = os.path.splitext(filename)
                            if ext.lower() not in [".inp", ".in", ".txt"]:
                                continue

                            inp_path = os.path.join(root, filename)
                            # tìm file out tương ứng
                            candidates = [
                                os.path.join(root, name + ".out"),
                                os.path.join(root, name + ".ans"),
                                os.path.join(root, name + ".txt"),
                            ]
                            out_path = next((p for p in candidates if os.path.exists(p)), None)
                            if not out_path:
                                skipped += 1
                                continue

                            try:
                                with open(inp_path, encoding="utf-8") as fi:
                                    inp_data = fi.read().strip()
                                with open(out_path, encoding="utf-8") as fo:
                                    out_data = fo.read().strip()

                                TestCase.objects.create(
                                    problem=problem,
                                    input_data=inp_data,
                                    expected_output=out_data,
                                )
                                imported += 1
                            except Exception as e:
                                print(f"⚠️ Error reading {filename}: {e}")
                                skipped += 1

                messages.success(
                    request,
                    f"✅ Đã import {imported} test case cho {problem.code}. "
                    f"⏩ Bỏ qua {skipped} file không hợp lệ hoặc thiếu cặp .out/.ans.",
                )
                # Trả về trang change của model admin theo tên route chuẩn
                change_url = reverse("admin:problems_problem_change", args=[problem.id])
                return redirect(change_url)
        else:
            form = UploadTestZipForm()

        return render(
            request,
            "admin/upload_tests.html",
            {"form": form, "problem": problem},
        )

    # -------------------------------
    # ⚙️ AJAX load testcases có phân trang
    # -------------------------------
    def load_tests(self, request, problem_id):
        page = int(request.GET.get("page", 1))
        per_page = 20

        problem = Problem.objects.get(pk=problem_id)
        testcases = TestCase.objects.filter(problem=problem).order_by("id")

        paginator = Paginator(testcases, per_page)
        page_obj = paginator.get_page(page)

        html = render_to_string(
            "admin/problems/testcase_list_partial.html",
            {"testcases": page_obj, "page_obj": page_obj},
            request=request,
        )

        return JsonResponse(
            {
                "html": html,
                "has_next": page_obj.has_next(),
                "next_page": page + 1 if page_obj.has_next() else None,
            }
        )
