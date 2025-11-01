from django.contrib import admin
from .models import Problem, ProblemTag
from django.utils.safestring import mark_safe
from django import forms
import markdown
from django.urls import reverse
from django.utils.html import format_html

class ProblemAdminForm(forms.ModelForm):
    """Form admin kèm Markdown preview + AI buttons"""

    class Meta:
        model = Problem
        fields = "__all__"
        widgets = {
            "statement": forms.Textarea(attrs={
                "rows": 20,
                "style": "font-family: Consolas, monospace;"
            })
        }

    class Media:
        css = {
            "all": [
                "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css",
                "/static/css/admin_markdown.css",
            ]
        }
        js = [
            "https://cdn.jsdelivr.net/npm/marked/marked.min.js",
            "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js",
            "https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js",
            "/static/js/admin_markdown.js",
            "/static/js/ai_admin_helper.js",
        ]

@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    form = ProblemAdminForm
    list_display = ("id", "title", "code", "difficulty", "ac_count", "submit_count")
    list_filter = ("difficulty", "tags")
    search_fields = ("title", "code")
    filter_horizontal = ("tags",)
    readonly_fields = ("preview_md", "ai_tools")

    def preview_md(self, obj):
        """Markdown + KaTeX preview dưới ô nhập"""
        return mark_safe("""
            <h3>📄 Preview</h3>
            <div id='preview-box' 
                 style='border:1px solid #ddd;padding:12px;border-radius:6px;background:#fff'></div>
        """)
    preview_md.short_description = "Preview"

    def ai_tools(self, obj):
        """Nút AI hỗ trợ nhập đề"""
        return format_html("""
            <h3>🤖 Công cụ AI</h3>
            <button type="button" class="button" onclick="ai_generate_problem()">✨ Sinh đề mới</button>
            <button type="button" class="button" onclick="ai_generate_samples()">🧪 Sinh Sample I/O</button>
            <button type="button" class="button" onclick="ai_check_format()">✅ Check format</button>
        """)
    ai_tools.short_description = "AI Tools"


@admin.register(ProblemTag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
