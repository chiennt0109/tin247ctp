# path: problems/admin.py
import os, zipfile, tempfile, io
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html

from .models import Problem, TestCase


class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "difficulty", "time_limit", "memory_limit", "view_tests_link")
    change_form_template = "admin/problems/change_form_with_upload.html"

    # ✅ Để hiển thị nút Upload Test
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.show_upload_button = True
        return form

    def get_urls(self):
        urls = super().get_urls()
        my = [
            path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
            path("<int:problem_id>/view_tests/", self.admin_site.admin_view(self.view_tests), name="view_tests"),
            path("<int:problem_id>/delete_test/<int:test_id>/", self.admin_site.admin_view(self.delete_test), name="delete_test"),
            path("<int:problem_id>/download_tests/", self.admin_site.admin_view(self.download_tests), name="download_tests"),
        ]
        return my + urls

    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">👁 Xem test</a>',
            reverse("admin:view_tests", args=[obj.id])
        )

    # ✅ Import test ZIP
    def upload_tests(self, request, problem_id):
    problem = Problem.objects.get(pk=problem_id)
    form = UploadTestZipForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        zip_file = request.FILES["zip_file"]
        imported = skipped = 0

        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "tests.zip")

            with open(zip_path, "wb") as f:
                for chunk in zip_file.chunks():
                    f.write(chunk)

            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(tmpdir)

            for root, _, files in os.walk(tmpdir):
                for file in files:
                    name, ext = os.path.splitext(file)
                    ext = ext.lower()

                    # Accept common input formats
                    if ext not in [".inp", ".in", ".txt"]:
                        continue

                    inp_path = os.path.join(root, file)
                    out_path = None

                    # Candidate output file names
                    base = name  # e.g. PS_EqualPoint
                    candidates = [
                        base + ".out", base + ".ans", base + ".txt",
                        file.replace(".inp", ".out"),
                        file.replace(".in", ".out"),
                    ]

                    # Same folder search
                    for cand in candidates:
                        cp = os.path.join(root, cand)
                        if os.path.exists(cp):
                            out_path = cp
                            break

                    # Search one level above if not found
                    if not out_path:
                        parent = os.path.dirname(root)
                        for cand in candidates:
                            cp = os.path.join(parent, cand)
                            if os.path.exists(cp):
                                out_path = cp
                                break

                    if not out_path:
                        skipped += 1
                        continue

                    # Read data
                    with open(inp_path, encoding="utf-8", errors="ignore") as fi:
                        input_data = fi.read().strip()
                    with open(out_path, encoding="utf-8", errors="ignore") as fo:
                        output_data = fo.read().strip()

                    TestCase.objects.create(
                        problem=problem,
                        input_data=input_data,
                        expected_output=output_data
                    )
                    imported += 1

        messages.success(request, f"✅ Đã import {imported} test • ❌ Bỏ qua {skipped}")
        return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

    return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    # ✅ View tests
    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {"problem": problem, "testcases": tests})

    # ✅ Delete test via Ajax
    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error"})

    # ✅ Export test zip
    def download_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem)

        buf = io.BytesIO()
        z = zipfile.ZipFile(buf, "w")

        for i, t in enumerate(tests, start=1):
            z.writestr(f"{problem.code}/test{i:02d}.inp", t.input_data)
            z.writestr(f"{problem.code}/test{i:02d}.out", t.expected_output)

        z.close()
        buf.seek(0)
        resp = HttpResponse(buf, content_type="application/zip")
        resp["Content-Disposition"] = f"attachment; filename={problem.code}_tests.zip"
        return resp
