# path: problems/admin.py

import os
import zipfile
import tempfile
import io

from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html

from .models import Problem, TestCase


# Form upload ZIP
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "difficulty", "time_limit", "memory_limit", "view_tests_link")

    # Template custom thay cho trang change_form default
    change_form_template = "admin/problems/change_form_with_upload.html"

    # ✅ Thêm show_upload_button vào context để template hiển thị nút Upload
    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    # Link Hiển thị danh sách test
    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">👁 Xem test</a>',
            reverse("admin:view_tests", args=[obj.id])
        )

    # Tạo URL riêng cho upload + xem + xóa + download test
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
            path("<int:problem_id>/view_tests/", self.admin_site.admin_view(self.view_tests), name="view_tests"),
            path("<int:problem_id>/delete_test/<int:test_id>/", self.admin_site.admin_view(self.delete_test), name="delete_test"),
            path("<int:problem_id>/download_tests/", self.admin_site.admin_view(self.download_tests), name="download_tests"),
        ]
        return custom + urls

    # ✅ Upload và import testcases từ ZIP
    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        form = UploadTestZipForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            zip_file = request.FILES["zip_file"]
            imported = skipped = 0

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "tests.zip")

                # Save file
                with open(zip_path, "wb") as f:
                    for chunk in zip_file.chunks():
                        f.write(chunk)

                # Extract all files
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(tmpdir)

                # Scan tất cả file .in / .inp / .txt
                for root, _, files in os.walk(tmpdir):
                    for filename in files:
                        name, ext = os.path.splitext(filename)
                        if ext.lower() not in [".in", ".inp", ".txt"]:
                            continue

                        inp_path = os.path.join(root, filename)
                        out_path = None

                        # Kiểm tra cùng folder
                        candidates = [
                            name + ".out", name + ".ans", name + ".txt",
                            filename.replace(".in", ".out"), filename.replace(".inp", ".out")
                        ]
                        for c in candidates:
                            cp = os.path.join(root, c)
                            if os.path.exists(cp):
                                out_path = cp
                                break

                        # Nếu chưa thấy thì check parent dir
                        if not out_path:
                            parent = os.path.dirname(root)
                            for c in [name + ".out", name + ".ans", name + ".txt"]:
                                cp = os.path.join(parent, c)
                                if os.path.exists(cp):
                                    out_path = cp
                                    break

                        if not out_path:
                            skipped += 1
                            continue

                        # Đọc input/output
                        with open(inp_path, encoding="utf-8", errors="ignore") as fi:
                            inp = fi.read().strip()
                        with open(out_path, encoding="utf-8", errors="ignore") as fo:
                            out = fo.read().strip()

                        TestCase.objects.create(problem=problem, input_data=inp, expected_output=out)
                        imported += 1

            messages.success(request, f"✅ Import {imported} test • 🚫 Bỏ qua {skipped}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    # ✅ View testcases
    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {"problem": problem, "testcases": tests})

    # ✅ Xóa test
    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error"})

    # ✅ Download toàn bộ testcases dưới dạng ZIP
    def download_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem)

        buf = io.BytesIO()
        z = zipfile.ZipFile(buf, "w")

        for idx, t in enumerate(tests, start=1):
            z.writestr(f"{problem.code}/test{idx:02d}.inp", t.input_data)
            z.writestr(f"{problem.code}/test{idx:02d}.out", t.expected_output)

        z.close()
        buf.seek(0)

        resp = HttpResponse(buf, content_type="application/zip")
        resp["Content-Disposition"] = f"attachment; filename={problem.code}_tests.zip"
        return resp
