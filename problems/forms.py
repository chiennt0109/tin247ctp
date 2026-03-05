# =====================================================
# 📁 problems/forms.py — FINAL VERSION
# =====================================================

from django import forms
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

    class Meta:
        model = Problem
        fields = "__all__"

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


    def clean(self):
        cleaned = super().clean()
        checker_type = cleaned.get("checker")
        checker_file = (cleaned.get("checker_file") or "").strip()
        if "checker" not in self.fields or "checker_file" not in self.fields:
            return cleaned
        if checker_type == CheckerType.CUSTOM and not checker_file:
            self.add_error("checker_file", "Custom Checker yêu cầu checker.cpp (checker_file).")
        return cleaned
