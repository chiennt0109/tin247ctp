# path: problems/admin.py

import os, zipfile, tempfile, io
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html
from .models import Problem, TestCase, Tag
# Form upload ZIP
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa test cases")


@admin.register(Problem)
class ProblemAdminForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = "__all__"

    # ✅ Force load đúng dữ liệu instance, không bị giữ cache
    statement = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 25,
                "style": "font-family:monospace;",
                "autocomplete": "off",       # 🔥 chống browser nhớ form
                "data-no-store": "true",     # 🔥 chống editor cache
            }
        )
    )

    input_spec = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5, "style": "font-family:monospace;"})
    )

    output_spec = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 5, "style": "font-family:monospace;"})
    )

    sample_input = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "style": "font-family:monospace;"})
    )

    sample_output = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 4, "style": "font-family:monospace;"})
    )


# ✅ Keep TestCase inline (KHÔNG thay đổi)
class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    form = ProblemAdminForm

    list_display = ("code", "title", "difficulty", "submission_count", "ac_count")
    search_fields = ("code", "title")
    inlines = [TestCaseInline]

    # Link mở trang xem test
    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" target="_blank">👁 Xem test</a>',
            reverse("admin:view_tests", args=[obj.id])
        )

    # ✅ UPLOAD TESTCASE — hỗ trợ 2 cấu trúc thư mục
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

                VALID_IN = (".in", ".inp", ".txt", ".IN", ".INP", ".TXT")
                VALID_OUT = (".out", ".ans", ".txt", ".OUT", ".ANS", ".TXT")

                def ignore_file(name):
                    return name.startswith('.') or "__MACOSX" in name or name.lower().endswith(".ds_store")

                for root, _, files in os.walk(tmpdir):
                    for filename in files:
                        if ignore_file(filename):
                            continue

                        name, ext = os.path.splitext(filename)
                        if ext not in VALID_IN:
                            continue

                        inp = os.path.join(root, filename)
                        out = None

                        # Try same folder matching
                        for oe in VALID_OUT:
                            candidate = os.path.join(root, name + oe)
                            if os.path.exists(candidate):
                                out = candidate
                                break

                        # Try folder-name pattern folder/test01/test01.out
                        if not out:
                            folder = os.path.basename(root)
                            for oe in VALID_OUT:
                                candidate = os.path.join(root, folder + oe)
                                if os.path.exists(candidate):
                                    out = candidate
                                    break

                        if not out:
                            skipped += 1
                            continue

                        with open(inp, encoding="utf-8", errors="ignore") as f:
                            inp_data = f.read().strip()
                        with open(out, encoding="utf-8", errors="ignore") as f:
                            out_data = f.read().strip()

                        TestCase.objects.create(problem=problem, input_data=inp_data, expected_output=out_data)
                        imported += 1

            messages.success(request, f"✅ Imported {imported} tests — 🚫 Skipped {skipped}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(request, "admin/problems/upload_tests.html", {"form": form, "problem": problem})

    # Xem test
    def view_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        tests = TestCase.objects.filter(problem=problem)
        return render(request, "admin/problems/view_tests.html", {"problem": problem, "testcases": tests})

    # Xoá test
    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error"})

    # Tải toàn bộ test về ZIP
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
