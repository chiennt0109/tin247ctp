import os
import zipfile
import tempfile
from django import forms
from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.core.paginator import Paginator
from .models import Problem, TestCase

# ✅ INLINE định nghĩa trước khi dùng
class TestCaseInline(admin.TabularInline):
    model = TestCase
    extra = 1
    fields = ("input_data", "expected_output")
    verbose_name = "Test case"
    verbose_name_plural = "Danh sách test case"
@admin.register(Problem)
class ProblemAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "time_limit", "memory_limit")
    search_fields = ("code", "title")
    inlines = [TestCaseInline]
    change_form_template = "admin/problems/change_form_with_upload.html"

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path("<int:problem_id>/upload_tests/",
                 self.admin_site.admin_view(self.upload_tests),
                 name="upload_tests"),
            path("<int:problem_id>/load_tests/",
                 self.admin_site.admin_view(self.load_tests),
                 name="load_tests"),
        ]
        return my_urls + urls

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_upload_button"] = True
        return super().change_view(request, object_id, form_url, extra_context)

    def load_tests(self, request, problem_id):
        """AJAX load test cases by page"""
        page = int(request.GET.get("page", 1))
        per_page = 20

        problem = Problem.objects.get(pk=problem_id)
        testcases = TestCase.objects.filter(problem=problem).order_by("id")
        paginator = Paginator(testcases, per_page)
        page_obj = paginator.get_page(page)

        html = render_to_string(
            "admin/problems/testcase_list_partial.html",
            {"testcases": page_obj, "page_obj": page_obj},
            request=request
        )

        return JsonResponse({
            "html": html,
            "has_next": page_obj.has_next(),
            "next_page": page + 1 if page_obj.has_next() else None
        })
