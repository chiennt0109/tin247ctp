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
            f = request.FILES["zip_file"]
            imported = skipped = 0

            with tempfile.TemporaryDirectory() as tmp:
                zip_path = os.path.join(tmp, "t.zip")
                with open(zip_path, "wb") as zf:
                    for c in f.chunks(): zf.write(c)

                with zipfile.ZipFile(zip_path) as z: z.extractall(tmp)

                valid_in = (".in", ".inp", ".txt")
                valid_out = (".out", ".ans", ".txt")

                for root, _, files in os.walk(tmp):
                    for fl in files:
                        name, ext = os.path.splitext(fl)
                        if ext not in valid_in: continue
                        inp = os.path.join(root, fl)
                        out = None
                        for oe in valid_out:
                            p2 = os.path.join(root, name + oe)
                            if os.path.exists(p2):
                                out = p2
                                break
                        if not out:
                            skipped += 1; continue

                        TestCase.objects.create(
                            problem=problem,
                            input_data=open(inp).read().strip(),
                            expected_output=open(out).read().strip()
                        )
                        imported += 1

            messages.success(request, f"✅ Imported {imported} | 🚫 Skipped {skipped}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(request, "admin/problems/upload_tests.html",
                      {"problem": problem, "form": form})

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
