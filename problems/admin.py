from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.http import JsonResponse
from .models import Problem, TestCase, Tag
from .ai_helper import gen_ai_hint, analyze_failed_test, recommend_next, build_learning_path

import zipfile, io, os

### ========== CUSTOM ADMIN ==========

class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 0


@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "title", "difficulty", "display_tags", "created_at")
    search_fields = ("title", "statement", "code")
    list_filter = ("difficulty", "tags")
    inlines = [TestCaseInline]

    fieldsets = (
        ("Thông tin chính", {
            "fields": ("title", "code", "difficulty", "tags")
        }),
        ("Đề bài", {
            "fields": ("statement",)
        }),
        #("Upload", {
         #   "fields": ("pdf_file", "zip_tests"),
        #}),
    )


    class Media:
        css = {
            "all": [
                "/static/css/admin_markdown.css",
                "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css",
            ]
        }
        js = [
            "/static/js/markdown-it.min.js",
            "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js",
            "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js",
            "/static/js/admin_ai_helper.js",
            "https://cdn.jsdelivr.net/npm/marked/marked.min.js",
            "https://cdn.jsdelivr.net/npm/katex/dist/katex.min.js",
            "/static/js/ai_editor.js",
        ]

    ### -------- Show Tags --------
    def display_tags(self, obj):
        return ", ".join(t.name for t in obj.tags.all()) or "-"
    display_tags.short_description = "Tags"

    ### -------- Custom Buttons (AI) --------
    change_form_template = "admin/problems/change_form_with_upload.html"

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



    def admin_ai_generate(self, request):
        title = request.POST.get("title", "")
        statement = ai_generate_statement(title)
        return JsonResponse({"statement": statement})

    def admin_ai_samples(self, request):
        statement = request.POST.get("statement", "")
        samples = ai_generate_samples(statement)
        return JsonResponse(samples)

    def admin_ai_check(self, request):
        text = request.POST.get("statement", "")
        msg = ai_check_format(text)
        return JsonResponse({"message": msg})

    def admin_ai_autotag(self, request):
        text = request.POST.get("statement", "")
        tags = ai_suggest_tags(text)
        tag_list = []
        for t in tags:
            tag, _ = Tag.objects.get_or_create(name=t)
            tag_list.append(t)
        return JsonResponse({"tags": tag_list})

    ### -------- Auto fill code, difficulty, tags --------
    def save_model(self, request, obj, form, change):
        # Auto generate code if empty
        if not obj.code:
            last = Problem.objects.all().order_by("-id").first()
            next_id = (last.id + 1) if last else 1
            obj.code = f"P{next_id:03d}"

        # Auto-difficulty based on keywords
        text = (obj.statement or "").lower()
        if not obj.difficulty:
            if any(w in text for w in ["dp", "graph", "bfs", "dfs", "n^2", "segment"]):
                obj.difficulty = "Hard"
            elif any(w in text for w in ["prefix", "sort", "binary", "stack"]):
                obj.difficulty = "Medium"
            else:
                obj.difficulty = "Easy"

        # Auto-tags simple rule
        tag_rules = {
            "prefix": "Prefix Sum",
            "sort": "Sorting",
            "search": "Binary Search",
            "graph": "Graph",
            "tree": "Tree",
            "dfs": "DFS",
            "bfs": "BFS",
            "dp": "Dynamic Programming",
            "mod": "Math",
            "prime": "Math",
            "gcd": "Math",
            "stack": "Stack",
            "queue": "Queue",
            "segment": "Segment Tree",
        }

        super().save_model(request, obj, form, change)

        for key, t in tag_rules.items():
            if key in text:
                tag, _ = Tag.objects.get_or_create(name=t)
                obj.tags.add(tag)

        # Handle ZIP import for testcases
        if obj.zip_tests:
            z = zipfile.ZipFile(obj.zip_tests)
            for name in z.namelist():
                if name.endswith(".in") or name.endswith(".inp"):
                    case_name = os.path.splitext(name)[0]
                    input_txt = z.read(name).decode("utf8")
                    out_file = case_name + ".out"
                    output_txt = z.read(out_file).decode("utf8") if out_file in z.namelist() else ""

                    TestCase.objects.create(
                        problem=obj,
                        input_data=input_txt,
                        output_data=output_txt
                    )
