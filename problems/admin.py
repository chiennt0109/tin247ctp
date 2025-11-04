# path: problems/admin.py
import os
import io
import re
import zipfile
import tempfile
from typing import Dict, Tuple, Optional

from django import forms
from django.contrib import admin, messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from .models import Problem, TestCase, Tag


# ----- Helpers -----

IN_EXTS = {".in", ".inp", ".txt"}
OUT_EXTS = {".out", ".ans", ".txt"}

def _is_input_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in IN_EXTS

def _is_output_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in OUT_EXTS

def _looks_like_test_dir(dirname: str) -> bool:
    """Trả về True nếu thư mục có dạng test01, test1, TEST02,..."""
    return bool(re.fullmatch(r"(?i)test\d+", dirname or ""))

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()

def _collect_pairs(root_tmp: str) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """
    Gom cặp input/output theo 2 cấu trúc bạn dùng:
    - Cấu trúc 1 (Classic):  thumuc/testXY.in  + thumuc/testXY.out
    - Cấu trúc 2 (Nested):   tenbai/testXY/tenbai.inp  + tenbai/testXY/tenbai.out
      (ở đây key là 'testXY' lấy theo tên thư mục cha)

    Trả về dict: key -> (inp_path, out_path)
    """
    pairs: Dict[str, Tuple[Optional[str], Optional[str]]] = {}

    for dirpath, _, files in os.walk(root_tmp):
        rel_dir = os.path.relpath(dirpath, root_tmp)
        parent = os.path.basename(rel_dir) if rel_dir != "." else ""

        for fname in files:
            name_no_ext, ext = os.path.splitext(fname)
            fpath = os.path.join(dirpath, fname)
            ext = ext.lower()

            # Bỏ qua file lạ
            if ext not in IN_EXTS and ext not in OUT_EXTS:
                continue

            # Heuristic lấy "case key"
            # 1) Nếu nằm trong folder testXX -> key = testXX
            # 2) Ngược lại: key = name_no_ext (Classic)
            if _looks_like_test_dir(parent):
                case_key = parent.lower()  # ví dụ 'test01'
            else:
                case_key = name_no_ext.lower()  # ví dụ 'test01'

            if case_key not in pairs:
                pairs[case_key] = (None, None)

            cur_inp, cur_out = pairs[case_key]

            if ext in IN_EXTS:
                cur_inp = fpath
            if ext in OUT_EXTS:
                # Tránh ghi đè nếu đã có .txt cho input
                cur_out = fpath

            pairs[case_key] = (cur_inp, cur_out)

    return pairs


# ----- Forms -----

class ProblemAdminForm(forms.ModelForm):
    class Meta:
        model = Problem
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tránh trình duyệt giữ cache nội dung cũ
        if self.instance and self.instance.pk:
            self.initial["statement"] = self.instance.statement


class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa test cases")


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0


# ----- Admin -----

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    form = ProblemAdminForm
    #inlines = [TestCaseInline]

    change_form_template = "admin/problems/change_form_with_upload.html"

    list_display = ("code", "title", "difficulty", "submission_count", "ac_count", "view_tests_link")
    search_fields = ("code", "title")

    # Link xem test ngay trên list
    def view_tests_link(self, obj):
        url = reverse("admin:view_tests", args=[obj.id])
        return format_html('<a href="{}">👁 Test</a>', url)

    # Đảm bảo extra_context để template cũ hoạt động
    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    # ----- Custom URLs trong namespace 'admin' -----
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            # Test management
            path("<int:problem_id>/tests/", self.admin_site.admin_view(self.view_tests), name="view_tests"),
            path("<int:problem_id>/upload-tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
            path("<int:problem_id>/tests/<int:test_id>/delete/", self.admin_site.admin_view(self.delete_test), name="delete_test"),
            path("<int:problem_id>/tests/download/", self.admin_site.admin_view(self.download_tests), name="download_tests"),

            # AI endpoints (giữ nguyên API cũ để JS gọi không lỗi)
            path("ai_generate/", self.admin_site.admin_view(self.admin_ai_generate), name="ai_generate"),
            path("ai_check/", self.admin_site.admin_view(self.admin_ai_check), name="ai_check"),
            path("ai_autotag/", self.admin_site.admin_view(self.admin_ai_autotag), name="ai_autotag"),
            path("ai_samples/", self.admin_site.admin_view(self.admin_ai_samples), name="ai_samples"),
        ]
        # Để {% url 'admin:view_tests' %} hoạt động: name trên đây + admin namespace là đủ
        return custom + urls

    # ----- Views: Tests -----

    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        form = UploadTestZipForm(request.POST or None, request.FILES or None)

        if request.method == "POST" and form.is_valid():
            zip_file = request.FILES["zip_file"]
            imported = 0
            skipped = 0

            with tempfile.TemporaryDirectory() as tmpdir:
                # Lưu file zip tạm
                tmp_zip = os.path.join(tmpdir, "tests.zip")
                with open(tmp_zip, "wb") as f:
                    for chunk in zip_file.chunks():
                        f.write(chunk)

                # Giải nén
                with zipfile.ZipFile(tmp_zip) as z:
                    z.extractall(tmpdir)

                # Gom cặp input/output theo 2 cấu trúc được hỗ trợ
                pairs = _collect_pairs(tmpdir)

                for key, (inp_path, out_path) in pairs.items():
                    if not inp_path or not out_path:
                        skipped += 1
                        continue
                    input_data = _read_text(inp_path)
                    expected_output = _read_text(out_path)
                    TestCase.objects.create(
                        problem=problem,
                        input_data=input_data,
                        expected_output=expected_output,
                    )
                    imported += 1

            messages.success(request, f"✅ Imported {imported} — 🚫 Skipped {skipped}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(
            request,
            "admin/problems/upload_tests.html",
            {"form": form, "problem": problem},
        )

    def view_tests(self, request, problem_id):
        return render(
            request,
            "admin/problems/view_tests.html",
            {
                "problem": Problem.objects.get(pk=problem_id),
                "testcases": TestCase.objects.filter(problem_id=problem_id).order_by("id"),
            },
        )

    def delete_test(self, request, problem_id, test_id):
        try:
            TestCase.objects.get(id=test_id, problem_id=problem_id).delete()
            return JsonResponse({"status": "ok"})
        except TestCase.DoesNotExist:
            return JsonResponse({"status": "error", "message": "Not found"}, status=404)

    def download_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        buf = io.BytesIO()
        z = zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED)

        for i, t in enumerate(TestCase.objects.filter(problem=problem).order_by("id"), 1):
            z.writestr(f"{problem.code}/test{i:02d}.inp", t.input_data or "")
            z.writestr(f"{problem.code}/test{i:02d}.out", t.expected_output or "")

        z.close()
        buf.seek(0)
        resp = HttpResponse(buf, content_type="application/zip")
        resp["Content-Disposition"] = f"attachment; filename={problem.code}_tests.zip"
        return resp

    # ----- Views: AI (giữ API ổn định để file JS gọi) -----

    def admin_ai_generate(self, request):
        """
        POST JSON: {title, statement}
        Return: {code, difficulty, tags: []}
        """
        try:
            data = request.json if hasattr(request, "json") else None
        except Exception:
            data = None

        if not data:
            # Fallback nếu không dùng JSON middleware
            import json
            try:
                data = json.loads(request.body.decode("utf-8"))
            except Exception:
                data = {}

        title = (data or {}).get("title", "") or ""
        statement = (data or {}).get("statement", "") or ""

        # Heuristics rất nhẹ để bạn sớm dùng được; có thể thay bằng model sau
        code = re.sub(r"[^A-Za-z0-9]+", "_", title).strip("_")
        code = (code[:20] or "PROB").upper()

        # Độ khó dựa vào độ dài đề + từ khoá
        lc = statement.lower()
        if any(k in lc for k in ["segment tree", "fenwick", "suffix array", "convex hull"]):
            difficulty = "Hard"
        elif any(k in lc for k in ["two pointers", "binary search", "dp", "prefix", "stack", "queue"]):
            difficulty = "Medium"
        else:
            difficulty = "Easy"

        # Tags đơn giản
        tags = []
        for kw, tg in [
            ("prefix", "Prefix Sum"),
            ("two pointers", "Two Pointers"),
            ("binary search", "Binary Search"),
            ("dp", "Dynamic Programming"),
            ("graph", "Graph"),
            ("string", "String"),
            ("greedy", "Greedy"),
            ("sort", "Sorting"),
            ("stack", "Stack"),
            ("queue", "Queue"),
        ]:
            if kw in lc and tg not in tags:
                tags.append(tg)

        return JsonResponse(
            {
                "code": code,
                "difficulty": difficulty,
                "tags": tags or ["General"],
            }
        )

    def admin_ai_check(self, request):
        # Trả kết quả giả lập kiểm tra LaTeX/Markdown
        return JsonResponse({"ok": True, "message": "No obvious LaTeX issues found."})

    def admin_ai_autotag(self, request):
        # Gợi ý 1 vài tag mặc định
        return JsonResponse({"tags": ["General", "Implementation"]})

    def admin_ai_samples(self, request):
        # Trả vài sample prompt
        samples = [
            "Sinh đề bài với mảng và truy vấn tổng đoạn.",
            "Sinh đề bài về xâu và đếm mẫu con.",
            "Sinh đề đồ thị dạng BFS/DFS cơ bản.",
        ]
        return JsonResponse({"samples": samples})
