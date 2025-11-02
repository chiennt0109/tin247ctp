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
    # problems/admin.py (chỉ thay hàm này trong class ProblemAdmin)

    def upload_tests(self, request, problem_id):
        from django.db import transaction
        problem = Problem.objects.get(pk=problem_id)
        form = UploadTestZipForm(request.POST or None, request.FILES or None)
    
        if request.method == "POST" and form.is_valid():
            zip_file = request.FILES["zip_file"]
    
            # Các đuôi hợp lệ
            ALLOW_TXT = False  # Đặt True nếu bạn muốn nhận cả .txt
            IN_EXTS  = {".in", ".inp"} | ({".txt"} if ALLOW_TXT else set())
            OUT_EXTS = {".out", ".ans"} | ({".txt"} if ALLOW_TXT else set())
    
            imported = 0
            skipped  = 0
            paired_missing_output = []
            found_pairs = []
    
            # Sẽ build 2 map:
            # 1) map_base_input  : basename -> path_input
            # 2) map_base_output : basename -> path_output
            # Và kịch bản B: nếu phát hiện thư mục in/out, sẽ ghép theo filename trong 2 folder
    
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = os.path.join(tmpdir, "tests.zip")
                with open(zip_path, "wb") as f:
                    for chunk in zip_file.chunks():
                        f.write(chunk)
    
                with zipfile.ZipFile(zip_path, "r") as z:
                    z.extractall(tmpdir)
    
                # Quét toàn bộ cây thư mục
                input_dirs  = []
                output_dirs = []
    
                map_base_input  = {}
                map_base_output = {}
    
                for root, _, files in os.walk(tmpdir):
                    # Nhận diện thư mục in/out phổ biến
                    folder = os.path.basename(root).lower()
                    if folder in {"in", "input"}:
                        input_dirs.append(root)
                    if folder in {"out", "output"}:
                        output_dirs.append(root)
    
                    for fname in files:
                        name, ext = os.path.splitext(fname)
                        full = os.path.join(root, fname)
                        ext_l = ext.lower()
    
                        # Bỏ các file ẩn hệ thống
                        if fname.startswith("._") or fname.startswith(".DS_Store"):
                            continue
    
                        if ext_l in IN_EXTS:
                            # Trường hợp A (cùng thư mục): gom theo basename
                            map_base_input.setdefault(name, []).append(full)
    
                        if ext_l in OUT_EXTS:
                            map_base_output.setdefault(name, []).append(full)
    
                def pick_one(path_list):
                    # Ưu tiên file “ngắn hơn” (tránh duplicate), hoặc cứ lấy cái đầu.
                    if not path_list:
                        return None
                    return sorted(path_list, key=lambda p: (len(os.path.basename(p)), p))[0]
    
                # Ưu tiên ghép theo A (cặp cùng thư mục — cùng basename)
                for base, inputs in map_base_input.items():
                    inp_path = pick_one(inputs)
                    out_path = pick_one(map_base_output.get(base, []))
                    if inp_path and out_path:
                        found_pairs.append((inp_path, out_path))
                    elif inp_path and not out_path:
                        paired_missing_output.append(os.path.basename(inp_path))
    
                # Nếu A ghép được 0 cặp và có cấu trúc B rõ ràng → thử B
                if not found_pairs and (input_dirs and output_dirs):
                    # Ghép theo filename trong 2 cây: cùng tên base
                    def collect(dir_roots, exts):
                        bag = {}
                        for d in dir_roots:
                            for root, _, files in os.walk(d):
                                for fname in files:
                                    name, ext = os.path.splitext(fname)
                                    if ext.lower() in exts:
                                        bag[name] = os.path.join(root, fname)
                        return bag
    
                    bag_in  = collect(input_dirs, IN_EXTS)
                    bag_out = collect(output_dirs, OUT_EXTS)
    
                    for base, inp_path in bag_in.items():
                        out_path = bag_out.get(base)
                        if out_path:
                            found_pairs.append((inp_path, out_path))
                        else:
                            paired_missing_output.append(os.path.basename(inp_path))
    
                # Ghi DB (atomic)
                with transaction.atomic():
                    for inp_path, out_path in found_pairs:
                        try:
                            with open(inp_path, "r", encoding="utf-8", errors="ignore") as fi:
                                inp = fi.read().strip()
                            with open(out_path, "r", encoding="utf-8", errors="ignore") as fo:
                                out = fo.read().strip()
    
                            TestCase.objects.create(
                                problem=problem,
                                input_data=inp,
                                expected_output=out
                            )
                            imported += 1
                        except Exception:
                            skipped += 1
    
            # Thông báo rõ xử lý
            extra = ""
            if paired_missing_output:
                extra = f" | Thiếu file output cho: {min(len(paired_missing_output),5)}+" \
                        f" ví dụ: {', '.join(paired_missing_output[:5])}"
    
            messages.success(
                request,
                f"✅ Imported: {imported} | ❌ Skipped: {skipped}{extra}"
            )
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
