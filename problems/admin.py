import os, zipfile, tempfile, io
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import reverse, path
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html

from .models import Problem, TestCase, Tag

# =======================
# Form Admin
# =======================
class ProblemAdminForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.initial["statement"] = self.instance.statement


class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa test cases")


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0


# =======================
# Problem Admin
# =======================
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    form = ProblemAdminForm
    inlines = [TestCaseInline]

    list_display = ("code", "title", "difficulty", "submission_count", "ac_count", "view_tests_link")
    search_fields = ("code", "title")

    # ------------- CUSTOM ADMIN URLS -------------
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("<int:problem_id>/upload-tests/", self.upload_tests, name="upload_tests"),
            path("<int:problem_id>/tests/", self.view_tests, name="view_tests"),
            path("<int:problem_id>/tests/<int:test_id>/delete/", self.delete_test, name="delete_test"),
            path("<int:problem_id>/tests/download/", self.download_tests, name="download_tests"),

            # AI endpoints
            path("ai_generate/", self.admin_ai_generate, name="ai_generate"),
            path("ai_autotag/", self.admin_ai_autotag, name="ai_autotag"),
            path("ai_fix/", self.admin_ai_fix, name="ai_fix"),
        ]
        return custom_urls + urls

    # ------------- LINK VIEW TEST -------------
    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}">👁 Xem test</a>',
            reverse("view_tests", args=[obj.id])
        )
    view_tests_link.short_description = "Test cases"

    # =======================
    # ✅ UPLOAD ZIP TEST (2 styles)
    # =======================
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

                with zipfile.ZipFile(zip_path) as z:
                    z.extractall(tmpdir)

                VALID_IN = (".in", ".inp", ".txt")
                VALID_OUT = (".out", ".ans", ".txt")

                # Walk through extracted zip
                for root, _, files in os.walk(tmpdir):
                    for file in files:
                        name, ext = os.path.splitext(file)
                        if ext not in VALID_IN:
                            continue

                        inp_path = os.path.join(root, file)
                        out_path = None

                        # match same base file
                        for oe in VALID_OUT:
                            candidate = os.path.join(root, name + oe)
                            if os.path.exists(candidate):
                                out_path = candidate
                                break

                        if not out_path:
                            skipped += 1
                            continue

                        # Save to DB
                        TestCase.objects.create(
                            problem=problem,
                            input_data=open(inp_path).read().strip(),
                            expected_output=open(out_path).read().strip()
                        )
                        imported += 1

            messages.success(request, f"✅ Đã import {imported} test — 🚫 Bỏ qua {skipped}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(request, "admin/problems/upload_tests.html",
                      {"form": form, "problem": problem})

    # =======================
    # VIEW TESTS
    # =======================
    def view_tests(self, request, problem_id):
        return render(request, "admin/problems/view_tests.html", {
            "problem": Problem.objects.get(pk=problem_id),
            "testcases": TestCase.objects.filter(problem_id=problem_id)
        })

    # =======================
    # DELETE TEST
    # =======================
    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error"})

    # =======================
    # DOWNLOAD TESTS
    # =======================
    def download_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        buffer = io.BytesIO()
        z = zipfile.ZipFile(buffer, "w")

        for i, t in enumerate(TestCase.objects.filter(problem=problem), 1):
            z.writestr(f"{problem.code}/test{i:02d}.inp", t.input_data)
            z.writestr(f"{problem.code}/test{i:02d}.out", t.expected_output)

        z.close()
        buffer.seek(0)

        response = HttpResponse(buffer, content_type="application/zip")
        response["Content-Disposition"] = f"attachment; filename={problem.code}_tests.zip"
        return response

    # =======================
    # AI BUTTON HANDLERS
    # =======================
    def admin_ai_generate(self, request):
        return JsonResponse({"ok": True, "msg": "AI tạo đề bài chưa nối backend!"})

    def admin_ai_autotag(self, request):
        return JsonResponse({"tags": ["array", "dp", "math"]})

    def admin_ai_fix(self, request):
        return JsonResponse({"result": "✅ LaTeX đã sửa!"})
