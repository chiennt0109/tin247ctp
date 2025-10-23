import os, zipfile, tempfile
from django import forms
from django.contrib import admin, messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html
from .models import Problem, TestCase


# ============================================================
# 🧩 FORM: Upload file ZIP chứa các test case (.inp/.out)
# ============================================================
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


# ============================================================
# 🧩 ADMIN: Giao diện quản lý Problem
# ============================================================
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "time_limit", "memory_limit", "view_tests_link")
    search_fields = ("code", "title")
    change_form_template = "admin/problems/change_form_with_upload.html"

    # -------------------------------
    # Liên kết xem test
    # -------------------------------
    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">👁 Xem test</a>',
            reverse("admin:view_tests", args=[obj.id])
        )
    view_tests_link.short_description = "Test cases"

    # -------------------------------
    # URL bổ sung
    # -------------------------------
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

    # -------------------------------
    # Upload ZIP testcases
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
                    imported, skipped = 0, 0
                    for root, _, files in os.walk(tmpdir):
                        for filename in files:
                            name, ext = os.path.splitext(filename)
                            if ext.lower() not in [".inp", ".in", ".txt"]:
                                continue
                            inp = os.path.join(root, filename)
                            out = next(
                                (os.path.join(root, n)
                                 for n in [name+".out", name+".ans", name+".txt"]
                                 if os.path.exists(os.path.join(root, n))),
                                None
                            )
                            if not out:
                                skipped += 1
                                continue
                            try:
                                with open(inp, encoding="utf-8") as fi:
                                    inp_data = fi.read().strip()
                                with open(out, encoding="utf-8") as fo:
                                    out_data = fo.read().strip()
                                TestCase.objects.create(
                                    problem=problem,
                                    input_data=inp_data,
                                    expected_output=out_data
                                )
                                imported += 1
                            except Exception:
                                skipped += 1
                messages.success(request,
                    f"✅ Đã import {imported} test case cho {problem.code} (bỏ qua {skipped}).")
                return redirect(reverse("admin:problems_problem_change", args=[problem.id]))
        else:
            form = UploadTestZipForm()
        return render(request, "admin/upload_tests.html", {"form": form, "problem": problem})

    # -------------------------------
    # Trang xem test case
    # -------------------------------
    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        testcases = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {
            "problem": problem,
            "testcases": testcases,
        })
