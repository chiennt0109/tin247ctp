# =============================================================
# 📁 File: problems/admin.py
# ✅ Chức năng trong file:
#   - Hiển thị Problem trong Django Admin
#   - Upload ZIP test theo 2 kiểu folder
#     ✅ test01.inp + test01.out
#     ✅ test01/test01.inp + test01.out
#   - Xem test trong giao diện admin
#   - Xoá từng test
#   - ✅ Download toàn bộ test thành ZIP
# =============================================================

import os, zipfile, tempfile, io
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html
from .models import Problem, TestCase


# ======================
# 📦 Form Upload ZIP Test
# ======================
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


# ======================
# 🧠 Problem Admin
# ======================
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "difficulty", "time_limit", "memory_limit", "view_tests_link")

    # ✅ Dùng custom template có nút Upload Test ZIP
    change_form_template = "admin/problems/change_form_with_upload.html"

    # ======================
    # 🔗 Custom route trong admin
    # ======================
    def get_urls(self):
        urls = super().get_urls()
        my = [
            # 📥 Upload ZIP test
            path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),

            # 👁 Xem test
            path("<int:problem_id>/view_tests/", self.admin_site.admin_view(self.view_tests), name="view_tests"),

            # 🗑 Xoá 1 test
            path("<int:problem_id>/delete_test/<int:test_id>/", self.admin_site.admin_view(self.delete_test), name="delete_test"),

            # 📤 Download toàn bộ test về ZIP
            path("<int:problem_id>/download_tests/", self.admin_site.admin_view(self.download_tests), name="download_tests"),
        ]
        return my + urls

    # ======================
    # 🔗 Link xem test (hiển thị trong list_display)
    # ======================
    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">👁 Xem test</a>',
            reverse("admin:view_tests", args=[obj.id])
        )

    # ======================
    # 📥 Upload & Parse ZIP test
    # ======================
    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        form = UploadTestZipForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            zip_file = request.FILES["zip_file"]
            imported = skipped = 0

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "tests.zip")

                # ✅ Lưu file tạm
                with open(zip_path, "wb") as f:
                    for chunk in zip_file.chunks():
                        f.write(chunk)

                # ✅ Giải nén
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(tmpdir)

                # ✅ Duyệt file theo 2 kiểu
                for root, _, files in os.walk(tmpdir):
                    for filename in files:
                        name, ext = os.path.splitext(filename)
                        if ext.lower() not in [".in", ".inp", ".txt"]:
                            continue

                        inp_path = os.path.join(root, filename)
                        out_path = None

                        # 🎯 Ưu tiên tìm .out cùng folder
                        for cand in [name + ".out", name + ".ans", name + ".txt",
                                     filename.replace(".in", ".out"), filename.replace(".inp", ".out")]:
                            cp = os.path.join(root, cand)
                            if os.path.exists(cp):
                                out_path = cp
                                break

                        # 🎯 Nếu không có thì dò folder cha
                        if not out_path:
                            parent = os.path.dirname(root)
                            for cand in [name + ".out", name + ".ans", name + ".txt"]:
                                cp = os.path.join(parent, cand)
                                if os.path.exists(cp):
                                    out_path = cp
                                    break

                        if not out_path:
                            skipped += 1
                            continue

                        # ✅ Đọc nội dung test
                        with open(inp_path, encoding="utf-8", errors="ignore") as fi:
                            input_data = fi.read().strip()
                        with open(out_path, encoding="utf-8", errors="ignore") as fo:
                            output_data = fo.read().strip()

                        # ✅ Lưu DB
                        TestCase.objects.create(problem=problem, input_data=input_data, expected_output=output_data)
                        imported += 1

            messages.success(request, f"✅ Import {imported} test • 🚫 Bỏ qua {skipped}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    # ======================
    # 👁 Trang xem test
    # ======================
    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {"problem": problem, "testcases": tests})

    # ======================
    # 🗑 Xoá test
    # ======================
    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error"})

    # ======================
    # 📤 Download toàn bộ test thành ZIP
    # ======================
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
