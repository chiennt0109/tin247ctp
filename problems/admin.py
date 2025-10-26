# path: problems/admin.py
import os, zipfile, tempfile
from django import forms
from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.utils.html import format_html
from .models import Problem, TestCase


class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "difficulty", "time_limit", "memory_limit", "view_tests_link")
    search_fields = ("code", "title")
    change_form_template = "admin/problems/change_form_with_upload.html"

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">👁 Xem test</a>',
            reverse("admin:view_tests", args=[obj.id])
        )
    view_tests_link.short_description = "Test cases"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("<int:problem_id>/upload_tests/",
                 self.admin_site.admin_view(self.upload_tests),
                 name="upload_tests"),
            path("<int:problem_id>/view_tests/",
                 self.admin_site.admin_view(self.view_tests),
                 name="view_tests"),
        ]
        return my_urls + urls

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

                    # ✅ Tìm tất cả file hợp lệ (.in / .inp)
                    for root, _, files in os.walk(tmpdir):
                        for filename in files:
                            name, ext = os.path.splitext(filename)
                            if ext.lower() not in [".in", ".inp", ".txt"]:
                                continue

                            inp_path = os.path.join(root, filename)
                            # Kiểu 1: flat → tìm .out/.ans cùng tên
                            out_candidates = [
                                name + ".out",
                                name + ".ans",
                                name + ".txt",
                                filename.replace(".inp", ".out"),
                                filename.replace(".in", ".out")
                            ]

                            out_path = None
                            # Nếu có thư mục cha (theo dạng testXY/tenbai.inp)
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

    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        testcases = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {
            "problem": problem,
            "testcases": testcases,
        })
