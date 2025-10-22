from django.contrib import admin
from .models import Problem, TestCase
from django import forms
from django.shortcuts import redirect, render
from django.urls import path
from django.contrib import messages
import zipfile, tempfile, os


# Form để upload file .zip
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa testcases")


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'time_limit', 'memory_limit')
    search_fields = ('code', 'title')

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("<int:problem_id>/upload_tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
        ]
        return my_urls + urls

    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)

        if request.method == "POST":
            form = UploadTestZipForm(request.POST, request.FILES)
            if form.is_valid():
                zip_file = request.FILES['zip_file']
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_path = os.path.join(tmpdir, "tests.zip")

                    # Lưu file tạm
                    with open(zip_path, "wb") as f:
                        for chunk in zip_file.chunks():
                            f.write(chunk)

                    # Giải nén
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(tmpdir)

                    imported = 0
                    for root, dirs, files in os.walk(tmpdir):
                        for f in files:
                            if f.endswith('.inp'):
                                base = f[:-4]
                                inp_path = os.path.join(root, f)
                                out_path = os.path.join(root, base + ".out")
                                if not os.path.exists(out_path):
                                    continue

                                with open(inp_path, encoding='utf-8') as fi:
                                    inp = fi.read().strip()
                                with open(out_path, encoding='utf-8') as fo:
                                    out = fo.read().strip()

                                TestCase.objects.create(
                                    problem=problem,
                                    input_data=inp,
                                    expected_output=out
                                )
                                imported += 1

                messages.success(request, f"✅ Đã import {imported} test case cho {problem.code}.")
                return redirect(f"/admin/problems/problem/{problem.id}/change/")

        else:
            form = UploadTestZipForm()

        return render(request, "admin/upload_tests.html", {"form": form, "problem": problem})
