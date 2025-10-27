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
        return format_html('<a href="{}" target="_blank">👁 Xem test</a>', reverse("admin:view_tests", args=[obj.id]))
    view_tests_link.short_description = "Test cases"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
           path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
            path("<int:problem_id>/view_tests/", self.admin_site.admin_view(self.view_tests), name="view_tests"),
            path("delete_test/<int:test_id>/", self.admin_site.admin_view(self.delete_test), name="delete_test"),
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
                    for root, _, files in os.walk(tmpdir):
                        for filename in files:
                            name, ext = os.path.splitext(filename)
                            if ext.lower() not in [".in", ".inp", ".txt"]:
                                continue
                            inp_path = os.path.join(root, filename)
                            out_candidates = [name + ".out", name + ".ans"]
                            out_path = next((os.path.join(root, c) for c in out_candidates if os.path.exists(os.path.join(root, c))), None)
                            if not out_path:
                                skipped += 1
                                continue
                            with open(inp_path, encoding="utf-8", errors="ignore") as fi, \
                                 open(out_path, encoding="utf-8", errors="ignore") as fo:
                                TestCase.objects.create(problem=problem, input_data=fi.read().strip(), expected_output=fo.read().strip())
                                imported += 1
                messages.success(request, f"✅ Import {imported} test cho {problem.code} (bỏ qua {skipped})")
                return redirect(reverse("admin:problems_problem_change", args=[problem.id]))
        else:
            form = UploadTestZipForm()
        return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        testcases = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {"problem": problem, "testcases": testcases})

    def delete_test(self, request, test_id):
        from django.http import HttpResponse
        if request.method == "DELETE":
            try:
                from .models import TestCase
                TestCase.objects.filter(pk=test_id).delete()
                return HttpResponse(status=204)
            except Exception:
                return HttpResponse(status=500)
        return HttpResponse(status=405)

