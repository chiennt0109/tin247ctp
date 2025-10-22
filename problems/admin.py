# app/problems/admin.py
import os, zipfile, tempfile
from django import forms
from django.contrib import admin, messages
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import path, reverse
from .models import Problem, TestCase

# Upload form
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "time_limit", "memory_limit")
    search_fields = ("code", "title")
    change_form_template = "admin/problems/change_form_with_upload.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
            path("<int:problem_id>/load_tests/", self.admin_site.admin_view(self.load_tests), name="load_tests"),
        ]
        return my_urls + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {"show_upload_button": True}
        return super().change_view(request, object_id, form_url, extra_context)

    # --- Upload ZIP ---
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
                                (os.path.join(root, n) for n in [name+".out", name+".ans", name+".txt"] if os.path.exists(os.path.join(root, n))),
                                None
                            )
                            if not out: skipped += 1; continue
                            try:
                                TestCase.objects.create(
                                    problem=problem,
                                    input_data=open(inp, encoding="utf-8").read().strip(),
                                    expected_output=open(out, encoding="utf-8").read().strip()
                                )
                                imported += 1
                            except Exception:
                                skipped += 1
                messages.success(request, f"✅ Đã import {imported} test case (bỏ qua {skipped}).")
                return redirect(reverse("admin:problems_problem_change", args=[problem.id]))
        else:
            form = UploadTestZipForm()
        return render(request, "admin/upload_tests.html", {"form": form, "problem": problem})

    # --- Load test qua AJAX ---
    def load_tests(self, request, problem_id):
        page = int(request.GET.get("page", 1))
        per_page = 20
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem).order_by("id")
        paginator = Paginator(tests, per_page)
        page_obj = paginator.get_page(page)
        html = render_to_string("admin/problems/testcase_list_partial.html",
                                {"testcases": page_obj, "page_obj": page_obj}, request=request)
        return JsonResponse({"html": html,
                             "has_next": page_obj.has_next(),
                             "next_page": page+1 if page_obj.has_next() else None})
