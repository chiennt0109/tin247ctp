# =====================================================
# 📁 problems/forms.py — FINAL VERSION
# =====================================================

from django import forms
from django.conf import settings
from django.http import QueryDict
from django.contrib.admin.widgets import FilteredSelectMultiple
from .models import Problem, Tag, CheckerType


class ProblemAdminForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=FilteredSelectMultiple("Tags", is_stacked=False),
        help_text="Giữ Ctrl/Cmd để chọn nhiều tag."
    )


    test_zip_file = forms.FileField(
        required=False,
        label="Upload test ZIP (optional)",
        help_text=(
            "Có thể upload test ngay khi tạo bài mới; hỗ trợ tối đa 1 GB "
            "dữ liệu sau giải nén."
        ),
    )
    checker_source_file = forms.FileField(
        required=False,
        label="checker.cpp (optional)",
        help_text="Dùng khi Checker = Custom Checker.",
    )

    class Meta:
        model = Problem
        fields = [
            "code", "title", "statement", "time_limit", "memory_limit",
            "difficulty", "tags", "has_editorial", "ai_supported",
            "checker", "checker_file", "checker_config",
            "test_zip_file", "checker_source_file",
        ]

    def __init__(self, *args, **kwargs):
        data = kwargs.get("data")

        if data:
            qd = QueryDict(mutable=True)
            qd.update(data)

            raw_tags = data.getlist("tags")
            tag_ids = []
            
            for t in raw_tags:
                t = t.strip()
                if not t:
                    continue
            
                # Nếu đã là ID (từ UI)
                if t.isdigit():
                    tag_ids.append(t)
                    continue
            
                # Nếu là tên mới (từ AI)
                obj, _ = Tag.objects.get_or_create(
                    name=t,
                    defaults={"slug": t.lower().replace(" ", "-")}
                )
                tag_ids.append(str(obj.id))
            
            qd.setlist("tags", tag_ids)
            kwargs["data"] = qd

        super().__init__(*args, **kwargs)
        self.fields["tags"].queryset = Tag.objects.all()

        missing = []
        for fname in ("checker", "checker_file", "checker_config"):
            try:
                Problem._meta.get_field(fname)
            except Exception:
                missing.append(fname)
        for fname in missing:
            self.fields.pop(fname, None)


    def clean(self):
        cleaned = super().clean()
        checker_type = cleaned.get("checker")
        checker_file = (cleaned.get("checker_file") or "").strip()
        if "checker" not in self.fields or "checker_file" not in self.fields:
            return cleaned
        if checker_type == CheckerType.CUSTOM and not checker_file:
            self.add_error("checker_file", "Custom Checker yêu cầu checker.cpp (checker_file).")
        return cleaned

    def clean_test_zip_file(self):
        upload = self.cleaned_data.get("test_zip_file")
        if not upload:
            return upload
        max_size = settings.PROBLEM_TEST_ZIP_MAX_UPLOAD_SIZE
        if upload.size > max_size:
            max_size_mb = max_size // (1024 * 1024)
            raise forms.ValidationError(
                f"File ZIP tải lên vượt quá giới hạn {max_size_mb} MB."
            )
        return upload
