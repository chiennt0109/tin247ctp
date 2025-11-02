import os, zipfile, tempfile, io
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import reverse, path
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html

from .models import Problem, TestCase, Tag

### FORM
class ProblemAdminForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.initial["statement"] = self.instance.statement

### Upload ZIP form
class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip test")

### Inline test
class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    form = ProblemAdminForm
    inlines = [TestCaseInline]
    change_form_template = "admin/problems/change_form_with_upload.html"
    list_display = ("code","title","difficulty","submission_count","ac_count","view_tests_link")
    search_fields = ("code","title")

    ### ✅ Custom URLs
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:problem_id>/upload-tests/",
                self.admin_site.admin_view(self.upload_tests),
                name="problems_problem_upload_tests",
            ),
            path(
                "<int:problem_id>/tests/",
                self.admin_site.admin_view(self.view_tests),
                name="problems_problem_view_tests",
            ),
            path(
                "<int:problem_id>/tests/<int:test_id>/delete/",
                self.admin_site.admin_view(self.delete_test),
                name="problems_problem_delete_test",
            ),
            path(
                "<int:problem_id>/tests/download/",
                self.admin_site.admin_view(self.download_tests),
                name="problems_problem_download_tests",
            ),
        ]
        return custom + urls

    ### ✅ Link xem test
    def view_tests_link(self, obj):
        return format_html(
            '<a href="{}" class="button" target="_blank">👁</a>',
            reverse("admin:problems_problem_view_tests", args=[obj.id])
        )
    view_tests_link.short_description = "Test cases"

    ### ✅ Upload ZIP xử lý test
    def upload_tests(self, request, problem_id):
    problem = Problem.objects.get(pk=problem_id)
    form = UploadTestZipForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        zip_file = request.FILES["zip_file"]
        imported = skipped = 0

        VALID_IN = (".in", ".inp", ".txt")
        VALID_OUT = (".out", ".ans", ".txt")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_zip = os.path.join(tmpdir, "tests.zip")

            # Lưu zip tạm
            with open(tmp_zip, "wb") as f:
                for chunk in zip_file.chunks():
                    f.write(chunk)

            # Giải nén
            with zipfile.ZipFile(tmp_zip) as z:
                z.extractall(tmpdir)

            # Duyệt tất cả file
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    # bỏ file rác hệ thống
                    if file.startswith("._") or file.lower().startswith("thumbs.db"):
                        continue

                    name, ext = os.path.splitext(file)
                    if ext.lower() not in VALID_IN:
                        continue

                    inp_path = os.path.join(root, file)
                    out_path = None

                    # Ghép output dựa trên basename + extension
                    for oe in VALID_OUT:
                        candidate = os.path.join(root, name + oe)
                        if os.path.exists(candidate):
                            out_path = candidate
                            break

                    if not out_path:
                        skipped += 1
                        continue

                    try:
                        with open(inp_path, encoding="utf-8", errors="ignore") as f_in:
                            inp = f_in.read().strip()

                        with open(out_path, encoding="utf-8", errors="ignore") as f_out:
                            out = f_out.read().strip()

                        TestCase.objects.create(
                            problem=problem,
                            input_data=inp,
                            expected_output=out
                        )
                        imported += 1

                    except Exception:
                        skipped += 1

        messages.success(request, f"✅ Imported {imported} — 🚫 Skipped {skipped}")
        return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

    return render(
        request,
        "admin/problems/upload_tests.html",
        {"form": form, "problem": problem}
    )

    ### ✅ View tests
    def view_tests(self, request, problem_id):
        return render(request, "admin/problems/view_tests.html", {
            "problem": Problem.objects.get(pk=problem_id),
            "testcases": TestCase.objects.filter(problem_id=problem_id)
        })

    ### ✅ Delete test
    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status":"ok"})
        except:
            return JsonResponse({"status":"error"})

    ### ✅ Download tests
    def download_tests(self, request, problem_id):
        p = Problem.objects.get(pk=problem_id)
        buff = io.BytesIO(); z = zipfile.ZipFile(buff,"w")

        for i,t in enumerate(TestCase.objects.filter(problem=p),1):
            z.writestr(f"{p.code}/test{i:02}.inp", t.input_data)
            z.writestr(f"{p.code}/test{i:02}.out", t.expected_output)

        z.close(); buff.seek(0)
        resp = HttpResponse(buff, content_type="application/zip")
        resp["Content-Disposition"] = f"attachment; filename={p.code}_tests.zip"
        return resp
