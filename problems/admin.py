# app/problems/admin.py
import os
import zipfile
import tempfile
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
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
# 🧩 ADMIN: Giao diện quản lý Problem + upload ZIP test case
# ============================================================
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "time_limit", "memory_limit")
    search_fields = ("code", "title")
    inlines = [TestCaseInline]

    # ⚡ Template override để thêm nút Upload ZIP trong admin
    change_form_template = "admin/problems/change_form_with_upload.html"

    # ------------------------------------------------------------
    # 🧭 Thêm URL mới: /admin/problems/problem/<id>/upload_tests/
    # ------------------------------------------------------------
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "<int:problem_id>/upload_tests/",
                self.admin_site.admin_view(self.upload_tests),
                name="upload_tests",
            ),
        ]
        return my_urls + urls

    # ------------------------------------------------------------
    # 🧭 Override change_view để truyền biến vào template
    # ------------------------------------------------------------
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        print("🟢 Using change_form_with_upload.html template")  # debug log
        return super().change_view(request, object_id, form_url, extra_context)

    # ------------------------------------------------------------
    # ⚙️ Hàm xử lý upload ZIP
    # ------------------------------------------------------------
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

                    # Giải nén toàn bộ file .zip vào thư mục tạm
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(tmpdir)

                    imported = 0
                    skipped = 0
                    for root, _, files in os.walk(tmpdir):
                        for filename in files:
                            name, ext = os.path.splitext(filename)
                            ext = ext.lower()
                            if ext not in [".inp", ".in", ".txt"]:
                                continue

                            inp_path = os.path.join(root, filename)

                            # tìm file output ứng với input này (.out / .ans / .txt)
                            candidates = [
                                os.path.join(root, name + ".out"),
                                os.path.join(root, name + ".ans"),
                                os.path.join(root, name + ".txt"),
                            ]
                            out_path = next((p for p in candidates if os.path.exists(p)), None)
                            if not out_path:
                                skipped += 1
                                continue

                            # đọc nội dung input / output
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
                return redirect(f"/admin/problems/problem/{problem.id}/change/")

        else:
            form = UploadTestZipForm()

        return render(
            request,
            "admin/upload_tests.html",
            {"form": form, "problem": problem},
        )

