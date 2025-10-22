from django.contrib import admin
from django import forms
from django.shortcuts import redirect, render
from django.urls import path
from django.contrib import messages
import zipfile, tempfile, os
from .models import Problem, TestCase


# ----- Form Upload ZIP -----
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


# ----- Inline thêm TestCase thủ công -----
class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1
    fields = ("input_data", "expected_output")
    verbose_name = "Test case"
    verbose_name_plural = "Danh sách test case"


# ----- Problem Admin -----
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "time_limit", "memory_limit")
    search_fields = ("code", "title")
    inlines = [TestCaseInline]  # Cho phép thêm test thủ công trực tiếp
    change_form_template = "admin/problems/change_form_with_upload.html"  # Template tùy chỉnh có nút upload ZIP

    # Tạo URL riêng cho chức năng upload
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
        ]
        return my_urls + urls

    # Xử lý upload .zip
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

                    # Giải nén
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(tmpdir)

                    imported = 0
                    for root, _, files in os.walk(tmpdir):
                        for f in files:
                            if f.endswith(".inp"):
                                base = f[:-4]
                                inp_path = os.path.join(root, f)
                                out_path = os.path.join(root, base + ".out")
                                if not os.path.exists(out_path):
                                    continue

                                with open(inp_path, encoding="utf-8") as fi:
                                    inp = fi.read().strip()
                                with open(out_path, encoding="utf-8") as fo:
                                    out = fo.read().strip()

                                TestCase.objects.create(problem=problem, input_data=inp, expected_output=out)
                                imported += 1

                messages.success(request, f"✅ Đã import {imported} test case cho {problem.code}.")
                return redirect(f"/admin/problems/problem/{problem.id}/change/")

        else:
            form = UploadTestZipForm()

        return render(request, "admin/upload_tests.html", {"form": form, "problem": problem})
