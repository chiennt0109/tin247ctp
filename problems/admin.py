# path: problems/admin.py

import os, zipfile, tempfile, io
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import reverse, path
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html

from .models import Problem, TestCase, Tag

# ✅ FORM sửa Problem — chống cache nội dung
class ProblemAdminForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ép load từ DB, tránh browser giữ nội dung cũ
        if self.instance:
            self.initial["statement"] = self.instance.statement


# ✅ Upload ZIP test
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa test cases")


# ✅ TestCase Inline
class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0


# ✅ Admin cho Problem
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    form = ProblemAdminForm
    inlines = [TestCaseInline]

    list_display = ("code", "title", "difficulty", "submission_count", "ac_count", "view_tests_link")
    search_fields = ("code", "title")

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:problem_id>/upload-tests/", self.upload_tests, name="upload_tests"),
            path("<int:problem_id>/tests/", self.view_tests, name="view_tests"),
            path("<int:problem_id>/tests/<int:test_id>/delete/", self.delete_test, name="delete_test"),
            path("<int:problem_id>/tests/download/", self.download_tests, name="download_tests"),
        ]
        return custom + urls

    def view_tests_link(self, obj):
        return format_html('<a href="{}">👁 Test</a>',
            reverse("admin:view_tests", args=[obj.id]))
    view_tests_link.short_description = "Test cases"

    # ✅ Upload test zip
    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        form = UploadTestZipForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            zip_file = request.FILES["zip_file"]
            imported = skipped = 0

            with tempfile.TemporaryDirectory() as tmpdir:
                path_zip = os.path.join(tmpdir, "t.zip")
                with open(path_zip, "wb") as f:
                    for c in zip_file.chunks(): f.write(c)
                with zipfile.ZipFile(path_zip) as z: z.extractall(tmpdir)

                VALID_IN = (".in", ".inp", ".txt")
                VALID_OUT = (".out", ".ans", ".txt")

                for root, _, files in os.walk(tmpdir):
                    for file in files:
                        name, ext = os.path.splitext(file)
                        if ext not in VALID_IN: continue
                        inp = os.path.join(root, file)
                        out = None
                        for oe in VALID_OUT:
                            c = os.path.join(root, name + oe)
                            if os.path.exists(c): out = c; break
                        if not out:
                            skipped += 1; continue

                        TestCase.objects.create(
                            problem=problem,
                            input_data=open(inp).read().strip(),
                            expected_output=open(out).read().strip()
                        )
                        imported += 1

            messages.success(request, f"✅ Imported {imported} — 🚫 Skipped {skipped}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    # ✅ View test
    def view_tests(self, request, problem_id):
        return render(request, "admin/problems/view_tests.html", {
            "problem": Problem.objects.get(pk=problem_id),
            "testcases": TestCase.objects.filter(problem_id=problem_id)
        })

    # ✅ Delete test
    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error"})

    # ✅ Download all tests
    def download_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        buf = io.BytesIO(); z = zipfile.ZipFile(buf, "w")

        for i,t in enumerate(TestCase.objects.filter(problem=problem),1):
            z.writestr(f"{problem.code}/test{i:02d}.inp", t.input_data)
            z.writestr(f"{problem.code}/test{i:02d}.out", t.expected_output)

        z.close(); buf.seek(0)
        resp = HttpResponse(buf, content_type="application/zip")
        resp["Content-Disposition"] = f"attachment; filename={problem.code}_tests.zip"
        return resp
