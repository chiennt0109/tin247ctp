# =====================================================
# 📁 File: problems/admin.py (Final Clean Version)
# =====================================================

import os
import io
import re
import zipfile
import tempfile
import subprocess
from typing import Dict, Tuple, Optional

from django import forms
from django.contrib import admin, messages
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.utils.html import format_html

from .models import (
    Problem,
    TestCase,
    Tag,
    UserProgress,
)
from .views_admin import ai_analyze_problem, ai_suggest_tags   # <-- AI thật
from .forms import ProblemAdminForm
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe

from .models import ProblemEditorial, EditorialPurchase

CHECKER_CUSTOM = "custom"

# ===== SANDBOX EXPORT PATH =====
SANDBOX_ROOT = "/srv/judge/testcases"
IN_EXTS = {".in", ".inp", ".txt"}
OUT_EXTS = {".out", ".ans", ".txt"}


# ========== HELPER FUNCTIONS ==========
def _is_input_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in IN_EXTS

def _is_output_file(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in OUT_EXTS

def _looks_like_test_dir(dirname: str) -> bool:
    return bool(re.fullmatch(r"(?i)test\d+", dirname or ""))

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read().strip()

def _collect_pairs(root_tmp: str) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    """Gom cặp input/output từ zip."""
    pairs = {}
    for dirpath, _, files in os.walk(root_tmp):
        rel_dir = os.path.relpath(dirpath, root_tmp)
        parent = os.path.basename(rel_dir) if rel_dir != "." else ""
        for fname in files:
            name_no_ext, ext = os.path.splitext(fname)
            fpath = os.path.join(dirpath, fname)
            ext = ext.lower()
            if ext not in IN_EXTS and ext not in OUT_EXTS:
                continue
            key = parent.lower() if _looks_like_test_dir(parent) else name_no_ext.lower()
            if key not in pairs:
                pairs[key] = (None, None)
            inp, out = pairs[key]
            if ext in IN_EXTS:
                inp = fpath
            if ext in OUT_EXTS:
                out = fpath
            pairs[key] = (inp, out)
    return pairs


def _compile_custom_checker(problem_code: str, checker_bytes: bytes) -> str:
    checker_dir = os.path.join(SANDBOX_ROOT, problem_code)
    os.makedirs(checker_dir, exist_ok=True)
    checker_cpp = os.path.join(checker_dir, "checker.cpp")
    checker_bin = os.path.join(checker_dir, "checker")

    with open(checker_cpp, "wb") as f:
        f.write(checker_bytes)

    cmd = ["g++", checker_cpp, "-O2", "-std=c++17", "-o", checker_bin]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "checker compile failed")
    os.chmod(checker_bin, 0o755)
    return checker_bin


def _compile_custom_checker_from_zip(problem_code: str, tmp_root: str) -> bool:
    for dirpath, _, files in os.walk(tmp_root):
        for fname in files:
            if fname.lower() == "checker.cpp":
                with open(os.path.join(dirpath, fname), "rb") as f:
                    _compile_custom_checker(problem_code, f.read())
                return True
    return False


# ========== FORMS ==========

class UploadTestZipForm(forms.Form):
    zip_file = forms.FileField(label="Chọn file .zip chứa test cases")
    checker_file = forms.FileField(
        label="checker.cpp (nếu dùng Custom Checker)",
        required=False,
    )


class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0


# ========== USER PROGRESS ==========
@admin.register(UserProgress)
class UserProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "status", "attempts", "best_score", "last_submit")
    list_filter = ("status",)
    search_fields = ("user__username", "problem__title", "problem__code")


from contests.models import Contest
from django.utils import timezone

def problem_in_running_contest(problem):
    now = timezone.now()
    return Contest.objects.filter(
        problems=problem,
        start_time__lte=now,
        end_time__gte=now,
    ).exists()


# ========== MAIN PROBLEM ADMIN ==========
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    form = ProblemAdminForm
    filter_horizontal = ("tags",)
    list_per_page = 50

    change_form_template = "admin/problems/change_form_with_upload.html"
    fieldsets = (
        (None, {
            "fields": (
                "code",
                "title",
                "statement",
                "time_limit",
                "memory_limit",
                "difficulty",
                "tags", 
                "has_editorial",
                "ai_supported",
                "checker_type",
                "checker_file",
                "checker_config",
            )
        }),
    )
    list_display = ("code", "title", "difficulty", "submission_count", "ac_count", "view_tests_link")
    search_fields = ("code", "title")

    # --- VIEW LINK ---
    def view_tests_link(self, obj):
        if not obj.id:
            return "—"
        url = reverse("admin:view_tests", args=[obj.id])
        return format_html('<a href="{}" target="_blank">👁 Test</a>', url)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = None
        if object_id:
            obj = Problem.objects.filter(pk=object_id).first()
    
        extra_context["show_upload_button"] = True
        extra_context["problem_locked"] = problem_in_running_contest(obj) if obj else False
    
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)


    # --- CUSTOM URLS ---
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path("<int:problem_id>/tests/", self.admin_site.admin_view(self.view_tests), name="view_tests"),
            path("<int:problem_id>/upload-tests/", self.admin_site.admin_view(self.upload_tests), name="upload_tests"),
            path("<int:problem_id>/tests/<int:test_id>/delete/", self.admin_site.admin_view(self.delete_test), name="delete_test"),
            path("<int:problem_id>/tests/download/", self.admin_site.admin_view(self.download_tests), name="download_tests"),
            path("sandbox/check/<int:problem_id>/", self.admin_site.admin_view(self.sandbox_check), name="sandbox_check"),

            # 🔥 AI endpoints — CHỈ DÙNG AI THẬT
            path("ai_analyze_problem/", self.admin_site.admin_view(ai_analyze_problem), name="ai_analyze_problem"),
            path("ai_suggest_tags/", self.admin_site.admin_view(ai_suggest_tags), name="ai_suggest_tags"),
        ]
        return custom + urls

    # --- UPLOAD TESTS ---
    def upload_tests(self, request, problem_id):
        problem = Problem.objects.get(pk=problem_id)
        form = UploadTestZipForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            zip_file = request.FILES["zip_file"]
            checker_upload = request.FILES.get("checker_file")
            imported = skipped = 0
            checker_compiled = False
            with tempfile.TemporaryDirectory() as tmpdir:
                tmp_zip = os.path.join(tmpdir, "tests.zip")
                with open(tmp_zip, "wb") as f:
                    for chunk in zip_file.chunks():
                        f.write(chunk)
                with zipfile.ZipFile(tmp_zip) as z:
                    z.extractall(tmpdir)
                pairs = _collect_pairs(tmpdir)
                sandbox_dir = os.path.join(SANDBOX_ROOT, problem.code)
                in_dir, out_dir = [os.path.join(sandbox_dir, sub) for sub in ("in", "out")]
                os.makedirs(in_dir, exist_ok=True)
                os.makedirs(out_dir, exist_ok=True)

                TestCase.objects.filter(problem=problem).delete()
                for d in (in_dir, out_dir):
                    for f in os.listdir(d):
                        os.remove(os.path.join(d, f))

                for i, (k, (inp, outp)) in enumerate(sorted(pairs.items()), 1):
                    if not inp or not outp:
                        skipped += 1
                        continue
                    in_data = _read_text(inp)
                    out_data = _read_text(outp)
                    TestCase.objects.create(problem=problem, input_data=in_data, expected_output=out_data)
                    with open(os.path.join(in_dir, f"{i:02d}.inp"), "w", encoding="utf-8") as fi:
                        fi.write(in_data + "\n")
                    with open(os.path.join(out_dir, f"{i:02d}.out"), "w", encoding="utf-8") as fo:
                        fo.write(out_data + "\n")
                    imported += 1

                if problem.checker_type == CHECKER_CUSTOM:
                    if checker_upload:
                        checker_bin = _compile_custom_checker(problem.code, checker_upload.read())
                        problem.checker_file = "checker.cpp"
                        problem.save(update_fields=["checker_file"])
                        checker_compiled = True
                    else:
                        checker_compiled = _compile_custom_checker_from_zip(problem.code, tmpdir)
                        if checker_compiled and not problem.checker_file:
                            problem.checker_file = "checker.cpp"
                            problem.save(update_fields=["checker_file"])
                        if not checker_compiled:
                            raise forms.ValidationError("Custom Checker cần checker.cpp (upload riêng hoặc nằm trong zip).")

            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "imported": imported, "skipped": skipped, "checker_compiled": checker_compiled, "message": f"Imported {imported}, skipped {skipped}."})

            messages.success(request, f"Imported {imported} — Skipped {skipped}. Checker compiled: {checker_compiled}")
            return redirect(reverse("admin:problems_problem_change", args=[problem.id]))

        return render(request, "admin/upload_tests.html", {"form": form, "problem": problem})

    # ----------------------
    # VIEW / DELETE / DOWNLOAD TESTS
    # ----------------------

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
            return JsonResponse({"status": "error", "message": "not found"}, status=404)

    def download_tests(self, request, problem_id):
        p = Problem.objects.get(pk=problem_id)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for i, t in enumerate(TestCase.objects.filter(problem=p).order_by("id"), 1):
                z.writestr(f"{p.code}/test{i:02d}.inp", t.input_data or "")
                z.writestr(f"{p.code}/test{i:02d}.out", t.expected_output or "")
        buf.seek(0)
        resp = HttpResponse(buf, content_type="application/zip")
        resp["Content-Disposition"] = f"attachment; filename={p.code}_tests.zip"
        return resp

    # ----------------------
    # SANDBOX CHECK
    # ----------------------

    def sandbox_check(self, request, problem_id):
        path = os.path.join(SANDBOX_ROOT, "_check", "ok.txt")
        ok = os.path.exists(path)
        return JsonResponse({"sandbox_ok": ok})



    # ==========================================================
    #  SAVE MODEL — hợp nhất logic rename + lock khi đang contest
    # ==========================================================
    def save_model(self, request, obj, form, change):
        import shutil

        # 🔒 Nếu đang trong contest thì không cho sửa code
        if obj.pk and problem_in_running_contest(obj):
            if "code" in form.changed_data:
                raise PermissionDenied("Bài toán đang trong kỳ thi – không thể sửa code.")

        # Nếu code thay đổi → đổi tên thư mục test
        if change:
            old_obj = Problem.objects.get(pk=obj.pk)
            old_code = old_obj.code
            new_code = obj.code

            if old_code != new_code:
                old_path = os.path.join(SANDBOX_ROOT, old_code)
                new_path = os.path.join(SANDBOX_ROOT, new_code)

                if os.path.exists(old_path):
                    try:
                        shutil.move(old_path, new_path)
                        messages.info(
                            request,
                            f"Đã đổi tên thư mục test từ '{old_code}' → '{new_code}'"
                        )
                    except Exception as e:
                        messages.error(
                            request,
                            f"Không thể đổi tên thư mục test ({e})"
                        )

        # Lưu model
        super().save_model(request, obj, form, change)

        # Lưu ManyToMany
        if hasattr(form, "save_m2m"):
            form.save_m2m()

        messages.success(request, "Lưu bài toán thành công!")


    def get_readonly_fields(self, request, obj=None):
        ro = list(super().get_readonly_fields(request, obj))
        if obj and problem_in_running_contest(obj):
            ro.append("code")
        return ro


    def render_change_form(self, request, context, *args, **kwargs):
        obj = kwargs.get("obj")
    
        try:
            adminform = context.get("adminform")
            form = adminform.form if adminform else None
    
            # Chỉ xử lý khi có form + có field "code"
            if obj and form and "code" in form.fields:
                if problem_in_running_contest(obj):
                    form.fields["code"].help_text = mark_safe(
                        "<span style='color:red;font-weight:bold'>⚠ Bài toán đang nằm trong kỳ thi đang diễn ra. Không thể sửa code.</span>"
                    )
        except Exception:
            # Tuyệt đối không cho crash admin — bỏ qua silently
            pass
    
        return super().render_change_form(request, context, *args, **kwargs)


@admin.register(ProblemEditorial)
class ProblemEditorialAdmin(admin.ModelAdmin):
    list_display = ("problem", "access_mode", "updated_at")
    search_fields = ("problem__code", "problem__title")
    autocomplete_fields = ("problem",)
    list_filter = ("access_mode",)
    class Media:
        css = {
            "all": [
                "https://uicdn.toast.com/editor/latest/toastui-editor.min.css",
                "https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.css",
            ]
        }
        js = [
            "https://uicdn.toast.com/editor/latest/toastui-editor-all.min.js",
            "https://cdn.jsdelivr.net/npm/katex@0.16.10/dist/katex.min.js",
            "/static/toastui/editorial_init.js",
        ]


@admin.register(EditorialPurchase)
class EditorialPurchaseAdmin(admin.ModelAdmin):
    list_display = ("user", "problem", "purchased_at")
    search_fields = ("user__username", "problem__code")
    autocomplete_fields = ("user", "problem")
