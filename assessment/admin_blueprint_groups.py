from django import forms
from django.contrib import admin, messages

from assessment.models import ExamBlueprint, ExamBlueprintGroup
from assessment.services.equivalence import validate_equivalence_group


class BlueprintGroupForm(forms.ModelForm):
    class BlueprintChoiceField(forms.ModelMultipleChoiceField):
        def label_from_instance(self, blueprint):
            version = blueprint.versions.filter(is_locked=True).order_by("-version").first()
            coverage = 0
            if version:
                coverage = len(set(version.sections.values_list(
                    "slots__curriculum_id", "slots__outcome_id",
                )))
            state = "READY" if blueprint.is_ready else "THIẾU"
            return (
                f"{blueprint.name} | {blueprint.total_questions} câu | "
                f"{blueprint.total_score} điểm | {blueprint.duration_minutes} phút | "
                f"coverage {coverage} | {state}"
            )

    blueprints = BlueprintChoiceField(
        queryset=ExamBlueprint.objects.all().order_by("name"),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = ExamBlueprintGroup
        fields = "__all__"


class ExamBlueprintGroupAdmin(admin.ModelAdmin):
    form = BlueprintGroupForm
    list_display = (
        "name", "code", "exam_type", "is_active", "selection_policy",
        "ready_count", "blueprint_count",
    )
    actions = ("validate_groups",)

    @admin.display(description="READY")
    def ready_count(self, obj):
        return obj.blueprints.filter(is_ready=True, is_locked=True).count()

    @admin.display(description="Tổng ma trận")
    def blueprint_count(self, obj):
        return obj.blueprints.count()

    @admin.action(description="Kiểm tra nhóm ma trận tương đương")
    def validate_groups(self, request, queryset):
        for group in queryset:
            rows = validate_equivalence_group(group)
            detail = "; ".join(
                f"{row['blueprint'].name}: "
                f"{'READY' if row['ready'] else 'THIẾU - ' + ', '.join(row['errors'])}"
                f"{' (Cảnh báo: ' + ', '.join(row['warnings']) + ')' if row['warnings'] else ''}"
                for row in rows
            )
            level = messages.SUCCESS if rows and all(row["ready"] for row in rows) else messages.ERROR
            self.message_user(request, f"{group.name}: {detail}", level)


def register_blueprint_group_admin(site=None):
    """Install exactly one canonical group admin, regardless of import order."""
    site = site or admin.site
    if site.is_registered(ExamBlueprintGroup):
        site.unregister(ExamBlueprintGroup)
    site.register(ExamBlueprintGroup, ExamBlueprintGroupAdmin)
