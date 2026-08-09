from django.contrib import admin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django import forms
from django.utils.text import slugify
from django.urls import path, reverse
from django.shortcuts import redirect, render
from django.db import transaction
from pathlib import Path
import tempfile

from assessment.models import (
    AssessmentAuditLog, AttemptAnswer, BankQuestion, BankQuestionRevision, BankSourceFile,
    BlueprintSection, BlueprintSlot, BlueprintVersion, CurriculumNode, CurriculumOutcome,
    ExamAccessGrant, ExamAttempt, ExamBlueprint, ExamBlueprintGroup, ExamResourcePackage,
    ExamSession, ExamUsageRecord, GeneratedExam, GeneratedExamQuestion,
    TrialAccountLink, TrialAuditEvent, TrialDevice, TrialEntitlement,
    GradingResult,
    QuestionAsset, QuestionSyncLog, ScoringRule, ScoringScheme, ScoringSchemeVersion,
)
from assessment.services.blueprint_versioning import clone_blueprint_version, lock_blueprint_version
from assessment.services.scoring_versioning import clone_scoring_version, lock_scoring_version
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.session_configuration import resolve_locked_configuration
from assessment.services.equivalence import validate_equivalence_group
from assessment.services.bank_importer import WorkbookBankImporter
from assessment.services.configuration_sync import MasterConfigurationSync
from assessment.services.admin_workflow import (
    close_exam_session, open_exam_session, prepare_blueprint, validate_session_ready,
)
from assessment.services.general_it_trial import grant_initial_trial
from assessment.admin_blueprint_groups import (
    BlueprintGroupForm, ExamBlueprintGroupAdmin, register_blueprint_group_admin,
)


# Django normally orders models alphabetically using their model-level
# ``verbose_name``.  The assessment workflow is easier to operate when the
# admin dashboard follows the actual business sequence instead.  Keep these
# presentation labels in the admin layer so changing the menu does not create
# schema migrations for the canonical projection models.
ASSESSMENT_ADMIN_MENU = {
    "BankQuestion": (10, "Ngân hàng câu hỏi"),
    "BankQuestionRevision": (20, "Phiên bản câu hỏi"),
    "QuestionAsset": (30, "Tài nguyên câu hỏi"),
    "BankSourceFile": (40, "Tệp nguồn ngân hàng"),
    "CurriculumNode": (50, "Chủ đề / mạch kiến thức"),
    "CurriculumOutcome": (60, "Yêu cầu cần đạt"),
    "QuestionSyncLog": (70, "Nhật ký đồng bộ ngân hàng"),
    "ExamBlueprint": (100, "Ma trận đề"),
    "ExamBlueprintGroup": (105, "Nhóm ma trận tương đương"),
    "BlueprintVersion": (110, "Phiên bản ma trận"),
    "BlueprintSection": (120, "Phần thi của ma trận"),
    "ScoringScheme": (200, "Quy tắc chấm điểm"),
    "ScoringSchemeVersion": (210, "Phiên bản quy tắc chấm"),
    "ExamSession": (300, "Kỳ kiểm tra"),
    "ExamAttempt": (400, "Bài làm và kết quả"),
    "GeneratedExam": (410, "Đề đã sinh theo bài làm"),
    "AttemptAnswer": (420, "Câu trả lời đã lưu"),
    "GradingResult": (430, "Kết quả chấm điểm"),
    "AssessmentAuditLog": (500, "Nhật ký thao tác kiểm tra"),
}
ASSESSMENT_PRIMARY_MODELS = {
    "BankQuestion", "ExamBlueprint", "ExamBlueprintGroup", "ExamSession", "ExamAttempt",
}


def _install_assessment_admin_menu():
    """Apply Vietnamese labels and workflow ordering to this admin site only."""
    if getattr(admin.site, "_assessment_menu_installed", False):
        return

    original_get_app_list = admin.site.get_app_list

    def get_app_list(request, app_label=None):
        app_list = original_get_app_list(request, app_label)
        for app in app_list:
            if app["app_label"] != "assessment":
                continue

            app["name"] = "Quản lý kiểm tra"
            advanced = request.user.is_superuser and request.GET.get("advanced") == "1"
            if not advanced:
                app["models"] = [
                    model for model in app["models"]
                    if model["object_name"] in ASSESSMENT_PRIMARY_MODELS
                ]
            for model in app["models"]:
                order, label = ASSESSMENT_ADMIN_MENU.get(
                    model["object_name"], (1000, model["name"]),
                )
                model["name"] = label
                model["assessment_order"] = order
            app["models"].sort(
                key=lambda model: (model["assessment_order"], model["name"]),
            )
        return app_list

    admin.site.get_app_list = get_app_list
    admin.site._assessment_menu_installed = True


class ReadOnlyProjectionAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.fields)


@admin.register(BankQuestion)
class BankQuestionAdmin(ReadOnlyProjectionAdmin):
    list_display = (
        "source_question_id", "question_type", "cognitive_level", "difficulty",
        "process_status", "is_available", "last_synced_at",
    )
    list_filter = ("question_type", "cognitive_level", "difficulty", "process_status", "is_available")
    search_fields = ("source_question_id", "source_code", "duplicate_family_id")
    list_select_related = ("curriculum", "outcome", "current_revision")


@admin.register(BankQuestionRevision)
class BankQuestionRevisionAdmin(ReadOnlyProjectionAdmin):
    list_display = ("question", "source_version", "content_hash", "synced_at")
    search_fields = ("question__source_question_id", "content_hash")
    exclude = ("protected_answer",)
    list_select_related = ("question",)


@admin.register(QuestionSyncLog)
class QuestionSyncLogAdmin(ReadOnlyProjectionAdmin):
    list_display = ("id", "mode", "status", "started_at", "completed_at", "initiated_by")
    list_filter = ("mode", "status")
    list_select_related = ("initiated_by",)


@admin.register(AssessmentAuditLog)
class AssessmentAuditLogAdmin(ReadOnlyProjectionAdmin):
    list_display = ("created_at", "action", "actor", "object_type", "object_id")
    list_filter = ("action", "object_type")
    search_fields = ("object_id", "actor__username")
    list_select_related = ("actor",)


admin.site.register(CurriculumNode, ReadOnlyProjectionAdmin)
admin.site.register(CurriculumOutcome, ReadOnlyProjectionAdmin)
admin.site.register(BankSourceFile, ReadOnlyProjectionAdmin)
admin.site.register(QuestionAsset, ReadOnlyProjectionAdmin)


class BlueprintSlotInline(admin.TabularInline):
    model = BlueprintSlot
    extra = 0
    fields = (
        "order", "curriculum", "outcome", "question_type", "cognitive_level", "difficulty",
        "quantity", "score_per_item", "requires_graduation_eligibility",
        "required_process_status",
    )

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.version.is_locked) and super().has_change_permission(request, obj)


@admin.register(BlueprintSection)
class BlueprintSectionAdmin(admin.ModelAdmin):
    list_display = ("name", "version", "order")
    list_select_related = ("version", "version__blueprint")
    inlines = (BlueprintSlotInline,)

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.version.is_locked) and super().has_change_permission(request, obj)


@admin.register(BlueprintVersion)
class BlueprintVersionAdmin(admin.ModelAdmin):
    list_display = (
        "blueprint", "version", "expected_question_count", "expected_total_score",
        "duration_minutes", "is_locked", "created_at",
    )
    list_filter = ("is_locked", "blueprint__exam_type", "blueprint__grade")
    list_select_related = ("blueprint", "created_by", "approved_by")
    readonly_fields = ("is_locked", "validation_report", "approved_at", "created_at")
    actions = ("lock_versions", "clone_versions")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_locked:
            return tuple(field.name for field in self.model._meta.fields)
        return self.readonly_fields

    @admin.action(description="Khóa phiên bản")
    def lock_versions(self, request, queryset):
        for version in queryset:
            try:
                session = version.exam_sessions.select_related("scoring_version").first()
                lock_blueprint_version(
                    version, scoring_version=session.scoring_version if session else None,
                    approver=request.user,
                )
            except (ValueError, ValidationError) as exc:
                self.message_user(request, f"{version}: {exc}", messages.ERROR)
            else:
                self.message_user(request, f"Đã khóa {version}.", messages.SUCCESS)

    @admin.action(description="Tạo bản sao để chỉnh sửa")
    def clone_versions(self, request, queryset):
        for version in queryset.filter(is_locked=True):
            clone = clone_blueprint_version(version, actor=request.user)
            self.message_user(request, f"Đã tạo {clone} ở trạng thái nháp.", messages.SUCCESS)


@admin.register(ExamBlueprint)
class ExamBlueprintAdmin(admin.ModelAdmin):
    change_list_template = "admin/assessment/examblueprint/change_list.html"
    list_display = (
        "name", "source_blueprint_id", "total_questions", "total_score",
        "duration_minutes", "is_locked", "is_ready", "difficulty_profile",
        "group_names",
    )
    list_filter = ("is_ready", "is_locked", "equivalence_groups", "exam_type", "grade")
    search_fields = ("name", "subject")
    list_select_related = ("created_by", "approved_by")
    readonly_fields = (
        "total_questions", "total_score", "duration_minutes", "difficulty_profile",
        "is_locked", "is_ready",
    )
    actions = ("prepare_blueprints", "check_blueprint_sources")

    @admin.display(description="Nhóm tương đương")
    def group_names(self, obj):
        return ", ".join(obj.equivalence_groups.values_list("name", flat=True)) or "-"

    @admin.action(description="Khóa và chuẩn bị ma trận")
    def prepare_blueprints(self, request, queryset):
        for blueprint in queryset:
            try:
                prepared = prepare_blueprint(blueprint, actor=request.user)
            except (ValidationError, ValueError) as exc:
                self.message_user(request, f"{blueprint}: {exc}", messages.ERROR)
            else:
                self.message_user(
                    request, f"{prepared}: LOCKED và READY.", messages.SUCCESS,
                )

    @admin.action(description="Kiểm tra nguồn câu")
    def check_blueprint_sources(self, request, queryset):
        for blueprint in queryset:
            version = blueprint.versions.order_by("-version").first()
            if version is None:
                self.message_user(request, f"{blueprint}: chưa có phiên bản.", messages.ERROR)
                continue
            report = BlueprintValidator().validate(version)
            detail = "; ".join(
                f"Slot {index}: cần {row['required']} / có {row['candidates']}"
                for index, row in enumerate(report["availability"], 1)
            )
            self.message_user(
                request, f"{blueprint}: {detail}",
                messages.SUCCESS if report["valid"] else messages.ERROR,
            )

    def get_urls(self):
        return [
            path(
                "import/", self.admin_site.admin_view(self.import_blueprints),
                name="assessment_examblueprint_import",
            ),
            *super().get_urls(),
        ]

    def import_blueprints(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied
        if request.method == "POST" and request.FILES.get("workbook"):
            upload = request.FILES["workbook"]
            if not upload.name.lower().endswith(".xlsx"):
                self.message_user(request, "Chỉ chấp nhận file .xlsx.", messages.ERROR)
            else:
                temporary = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
                try:
                    for chunk in upload.chunks():
                        temporary.write(chunk)
                    temporary.close()
                    parsed = WorkbookBankImporter().parse(temporary.name)
                    if parsed.has_fatal_errors:
                        self.message_user(request, "Workbook không hợp lệ; không có dữ liệu được ghi.", messages.ERROR)
                    else:
                        with transaction.atomic():
                            report = MasterConfigurationSync().apply(parsed, actor=request.user)
                        self.message_user(
                            request,
                            f"Import hoàn tất: tạo {report['created']}, cập nhật {report['updated']} ma trận.",
                            messages.SUCCESS,
                        )
                        return redirect(reverse("admin:assessment_examblueprint_changelist"))
                finally:
                    temporary.close()
                    Path(temporary.name).unlink(missing_ok=True)
        return render(request, "admin/assessment/examblueprint/import.html", {
            **self.admin_site.each_context(request), "title": "Import ma trận từ Excel",
            "opts": self.model._meta,
        })


register_blueprint_group_admin(admin.site)


class ScoringRuleInline(admin.TabularInline):
    model = ScoringRule
    extra = 0

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_locked) and super().has_change_permission(request, obj)

    def has_add_permission(self, request, obj=None):
        return not (obj and obj.is_locked) and super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return not (obj and obj.is_locked) and super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_locked:
            return tuple(
                field.name for field in self.model._meta.fields
                if field.name not in {"id", "version"}
            )
        return ()


@admin.register(ScoringSchemeVersion)
class ScoringSchemeVersionAdmin(admin.ModelAdmin):
    list_display = ("scheme", "version", "total_score", "rounding_digits", "is_locked")
    list_filter = ("is_locked",)
    list_select_related = ("scheme", "created_by")
    inlines = (ScoringRuleInline,)
    readonly_fields = ("is_locked", "created_at")
    actions = ("lock_versions", "clone_versions")

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.is_locked:
            return tuple(field.name for field in self.model._meta.fields)
        return self.readonly_fields

    @admin.action(description="Khóa phiên bản")
    def lock_versions(self, request, queryset):
        for version in queryset:
            try:
                session = version.exam_sessions.select_related("blueprint_version").first()
                lock_scoring_version(
                    version, blueprint_version=session.blueprint_version if session else None,
                    actor=request.user,
                )
            except ValidationError as exc:
                self.message_user(request, f"{version}: {'; '.join(exc.messages)}", messages.ERROR)
            else:
                self.message_user(request, f"Đã khóa {version}.", messages.SUCCESS)

    @admin.action(description="Tạo bản sao để chỉnh sửa")
    def clone_versions(self, request, queryset):
        for version in queryset.filter(is_locked=True):
            clone = clone_scoring_version(version, actor=request.user)
            self.message_user(request, f"Đã tạo {clone} ở trạng thái nháp.", messages.SUCCESS)


@admin.register(ScoringScheme)
class ScoringSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default", "created_by", "created_at")
    search_fields = ("name",)
    list_select_related = ("created_by",)


class ExamAttemptInline(admin.TabularInline):
    model = ExamAttempt
    extra = 0
    can_delete = False
    fields = ("user", "attempt_number", "status", "generated_exam", "started_at", "expires_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class ExamAccessGrantInline(admin.TabularInline):
    model = ExamAccessGrant
    extra = 0
    verbose_name = "Quyền và lượt làm của người dùng / nhóm"
    verbose_name_plural = "Quyền và lượt làm riêng"
    fields = (
        "user", "group", "limit_mode", "max_attempts", "valid_from", "valid_until",
        "is_active", "allow_download", "grant_source",
    )
    readonly_fields = ("grant_source",)
    autocomplete_fields = ("user", "group")


class ExamSessionAdminForm(forms.ModelForm):
    blueprint = forms.ModelChoiceField(
        queryset=ExamBlueprint.objects.all().order_by("name"), label="Ma trận đơn",
        help_text="Hệ thống tự chọn phiên bản ma trận và quy tắc chấm đã khóa mới nhất.",
        required=False,
    )

    class Meta:
        model = ExamSession
        fields = (
            "name", "blueprint_group", "blueprint", "opens_at", "closes_at",
            "duration_minutes", "max_attempts", "access_mode", "access_groups", "access_grades",
            "allow_signup_trial",
            "score_release_mode", "score_release_at", "answer_release_mode", "answer_release_at",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        max_attempts = self.fields.get("max_attempts")
        if max_attempts is not None:
            max_attempts.label = "Số lượt mặc định"
            max_attempts.help_text = (
                "Chỉ áp dụng cho các chế độ quyền cũ; chế độ cấp quyền riêng dùng từng dòng bên dưới."
            )
        if not self.instance._state.adding and self.instance.blueprint_version_id:
            blueprint = self.fields.get("blueprint")
            if blueprint is not None:
                blueprint.initial = self.instance.blueprint_version.blueprint_id
                if self.instance.status != ExamSession.Status.DRAFT:
                    blueprint.disabled = True

    def clean(self):
        cleaned = super().clean()
        if not self.instance._state.adding and self.instance.status != ExamSession.Status.DRAFT:
            return cleaned
        blueprint = cleaned.get("blueprint")
        group = cleaned.get("blueprint_group")
        if self.instance._state.adding and cleaned.get("name"):
            base = slugify(cleaned["name"]) or "ky-thi"
            slug = base
            suffix = 2
            while ExamSession.objects.filter(slug=slug).exists():
                slug = f"{base}-{suffix}"
                suffix += 1
            self.instance.slug = slug
        if group:
            self.instance.exam_type = group.exam_type
            rows = validate_equivalence_group(group, persist=False)
            configuration = None
            for row in rows:
                if row["version"] is None:
                    continue
                try:
                    configuration = resolve_locked_configuration(row["blueprint"])
                except ValidationError:
                    continue
                break
            if configuration is None:
                self.add_error(
                    "blueprint_group",
                    "Nhóm chưa có ma trận với phiên bản ma trận và quy tắc chấm đã LOCKED.",
                )
            else:
                self.instance.blueprint_version, self.instance.scoring_version = configuration
        elif blueprint:
            self.instance.exam_type = blueprint.exam_type
            try:
                blueprint_version, scoring_version = resolve_locked_configuration(blueprint)
            except ValidationError as exc:
                self.add_error("blueprint", exc)
            else:
                self.instance.blueprint_version = blueprint_version
                self.instance.scoring_version = scoring_version
        else:
            self.add_error("blueprint", "Chọn nhóm ma trận hoặc một ma trận đơn.")
        return cleaned


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    form = ExamSessionAdminForm
    readonly_fields = ("status",)
    list_display = (
        "name", "exam_type", "opens_at", "closes_at", "status",
    )
    list_filter = ("status", "exam_type", "score_release_mode", "answer_release_mode")
    search_fields = ("name", "slug")
    list_select_related = ("blueprint_version", "scoring_version", "created_by")
    filter_horizontal = ("access_groups",)
    inlines = (ExamAccessGrantInline, ExamAttemptInline)
    actions = (
        "check_generation_capacity", "open_sessions", "close_sessions",
        "delete_empty_or_cancel_sessions",
    )

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != ExamSession.Status.DRAFT:
            return tuple(
                field for field in ExamSessionAdminForm.Meta.fields
                if field not in {"blueprint", "allow_signup_trial"}
            ) + ("status",)
        return self.readonly_fields

    def save_formset(self, request, form, formset, change):
        if formset.model is ExamAccessGrant:
            if hasattr(formset, "deleted_objects"):
                instances = formset.save(commit=False)
                for deleted in formset.deleted_objects:
                    deleted.delete()
                for grant in instances:
                    # Once an administrator changes an automatic row, it is an
                    # explicit administrator decision and trial review/revocation
                    # must never alter it again.
                    grant.grant_source = ExamAccessGrant.GrantSource.ADMIN
                    grant.save()
                formset.save_m2m()
            else:
                formset.save()
        else:
            formset.save()
        if formset.model is ExamAccessGrant and form.instance.access_grants.filter(is_active=True).exists():
            ExamSession.objects.filter(pk=form.instance.pk).update(
                access_mode=ExamSession.AccessMode.ACCESS_GRANTS,
            )
            form.instance.access_mode = ExamSession.AccessMode.ACCESS_GRANTS

    @admin.action(description="Kiểm tra khả năng sinh đề")
    def check_generation_capacity(self, request, queryset):
        for session in queryset:
            try:
                validate_session_ready(session)
            except ValidationError as exc:
                self.message_user(request, f"{session.name}: {exc}", messages.ERROR)
            else:
                self.message_user(
                    request, f"{session.name}: đủ điều kiện mở kỳ thi.", messages.SUCCESS,
                )

    @admin.action(description="Mở kỳ thi")
    def open_sessions(self, request, queryset):
        for session in queryset:
            try:
                opened = open_exam_session(session)
            except ValidationError as exc:
                self.message_user(request, f"{session.name}: {exc}", messages.ERROR)
            else:
                self.message_user(
                    request, f"{opened.name}: {opened.get_status_display()}.", messages.SUCCESS,
                )

    @admin.action(description="Đóng kỳ thi")
    def close_sessions(self, request, queryset):
        for session in queryset:
            closed = close_exam_session(session)
            self.message_user(request, f"{closed.name}: Đã đóng.", messages.SUCCESS)

    @admin.action(description="Xóa kỳ thi trống / hủy kỳ thi đã có bài làm")
    def delete_empty_or_cancel_sessions(self, request, queryset):
        deleted = cancelled = 0
        for session in queryset:
            if session.attempts.exists() or session.generated_exams.exists():
                if session.status != ExamSession.Status.CANCELLED:
                    session.status = ExamSession.Status.CANCELLED
                    session.save(update_fields=("status", "updated_at"))
                cancelled += 1
            else:
                session.delete()
                deleted += 1
        self.message_user(
            request,
            f"Đã xóa {deleted} kỳ thi trống; đã hủy {cancelled} kỳ thi có lịch sử bài làm.",
            messages.SUCCESS,
        )

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj)


class GeneratedExamQuestionInline(admin.TabularInline):
    model = GeneratedExamQuestion
    extra = 0
    can_delete = False
    fields = ("order", "question_id_snapshot", "source_version_snapshot", "score", "content_hash_snapshot")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(GeneratedExam)
class GeneratedExamAdmin(ReadOnlyProjectionAdmin):
    list_display = ("code", "session", "total_score", "exam_hash", "is_locked", "generated_at")
    search_fields = ("code", "session__name", "exam_hash")
    list_filter = ("is_locked", "session__exam_type")
    list_select_related = ("session", "blueprint_version", "scoring_version", "generated_by")
    inlines = (GeneratedExamQuestionInline,)


@admin.register(ExamAttempt)
class ExamAttemptAdmin(ReadOnlyProjectionAdmin):
    list_display = (
        "id", "user", "session", "attempt_number", "status", "generated_exam",
        "started_at", "expires_at",
    )
    list_filter = ("status", "session__exam_type")
    search_fields = ("user__username", "session__name", "generated_exam__code")
    list_select_related = ("user", "session", "generated_exam")


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(ReadOnlyProjectionAdmin):
    list_display = ("attempt", "exam_question", "flagged_for_review", "saved_at")
    search_fields = ("attempt__user__username", "attempt__session__name")
    list_select_related = ("attempt", "attempt__user", "exam_question")


@admin.register(GradingResult)
class GradingResultAdmin(ReadOnlyProjectionAdmin):
    list_display = (
        "attempt", "sequence", "total_score", "max_score", "is_current", "created_at",
    )
    list_filter = ("is_current", "scoring_version")
    search_fields = ("attempt__user__username", "attempt__session__name")
    list_select_related = ("attempt", "attempt__user", "attempt__session", "scoring_version")


_install_assessment_admin_menu()


@admin.register(ExamUsageRecord)
class ExamUsageRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "exam_session", "usage_type", "status", "created_at", "committed_at")
    list_filter = ("usage_type", "status")
    search_fields = ("user__username", "exam_session__name", "idempotency_key")
    readonly_fields = (
        "user", "exam_session", "usage_type", "status", "exam_attempt",
        "resource_package", "idempotency_key", "created_at", "committed_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(ExamResourcePackage)
class ExamResourcePackageAdmin(admin.ModelAdmin):
    list_display = ("session", "user", "blueprint_version", "status", "created_at", "last_downloaded_at")
    list_filter = ("status", "session")
    search_fields = ("user__username", "session__name", "content_hash")
    readonly_fields = (
        "user", "session", "generated_exam", "blueprint", "blueprint_version",
        "seed", "question_snapshot", "answer_snapshot", "scoring_snapshot",
        "manifest", "content_hash", "status", "created_at", "last_downloaded_at",
    )

    def has_add_permission(self, request):
        return False


@admin.register(TrialEntitlement)
class TrialEntitlementAdmin(admin.ModelAdmin):
    list_display = (
        "id", "status", "account_count",
        "is_verified", "created_reason", "created_at",
    )
    list_filter = ("status", "is_verified", "created_reason")
    search_fields = ("account_links__user__username", "account_links__user__email")
    readonly_fields = ("created_at",)
    actions = ("mark_verified", "revoke")

    def save_model(self, request, obj, form, change):
        old = TrialEntitlement.objects.filter(pk=obj.pk).first() if change else None
        super().save_model(request, obj, form, change)
        if old and any(
            getattr(old, field) != getattr(obj, field)
            for field in ("status", "is_verified")
        ):
            self._audit(request, obj, "ADMIN_ENTITLEMENT_CHANGED", {
                "status_from": old.status, "status_to": obj.status,
            })

    @admin.display(description="Số tài khoản")
    def account_count(self, obj):
        return obj.account_links.count()

    def _audit(self, request, obj, event_type, details=None):
        TrialAuditEvent.objects.create(
            entitlement=obj, actor=request.user, event_type=event_type, details=details or {},
        )

    @admin.action(description="Đánh dấu hợp lệ")
    def mark_verified(self, request, queryset):
        for obj in queryset:
            obj.status = TrialEntitlement.Status.ACTIVE
            obj.is_verified = True
            obj.reviewed_by = request.user
            obj.save(update_fields=("status", "is_verified", "reviewed_by"))
            self._audit(request, obj, "ADMIN_VERIFIED")

    @admin.action(description="Thu hồi trial")
    def revoke(self, request, queryset):
        for obj in queryset:
            obj.status = TrialEntitlement.Status.REVOKED
            obj.reviewed_by = request.user
            obj.save(update_fields=("status", "reviewed_by"))
            grant_ids = obj.audit_events.filter(
                event_type="TRIAL_ACCESS_GRANT_CREATED",
            ).values_list("details__grant_id", flat=True)
            ExamAccessGrant.objects.filter(
                pk__in=list(grant_ids),
                grant_source=ExamAccessGrant.GrantSource.AUTO_TRIAL,
            ).update(is_active=False)
            self._audit(request, obj, "ADMIN_REVOKED")


@admin.register(TrialAccountLink)
class TrialAccountLinkAdmin(admin.ModelAdmin):
    list_display = ("user", "entitlement", "created_at")
    search_fields = ("user__username", "user__email")
    autocomplete_fields = ("user", "entitlement")
    list_select_related = ("user", "entitlement")
    actions = ("grant_trial_access",)

    @admin.action(description="Cấp quyền dùng thử bằng cơ chế quyền kỳ thi hiện tại")
    def grant_trial_access(self, request, queryset):
        for link in queryset.select_related("user", "entitlement"):
            if not link.user:
                continue
            grants = grant_initial_trial(
                link.user, actor=request.user, entitlement=link.entitlement,
            )
            if grants:
                link.entitlement.status = TrialEntitlement.Status.ACTIVE
                link.entitlement.is_verified = True
                link.entitlement.reviewed_by = request.user
                link.entitlement.save(update_fields=("status", "is_verified", "reviewed_by"))

    def save_model(self, request, obj, form, change):
        old = TrialAccountLink.objects.filter(pk=obj.pk).first() if change else None
        super().save_model(request, obj, form, change)
        if old and old.entitlement_id != obj.entitlement_id:
            TrialAuditEvent.objects.create(
                entitlement=obj.entitlement, user=obj.user, actor=request.user,
                event_type="ADMIN_ACCOUNT_RELINKED",
                details={"from": old.entitlement_id, "to": obj.entitlement_id},
            )


@admin.register(TrialDevice)
class TrialDeviceAdmin(admin.ModelAdmin):
    list_display = ("short_hash", "entitlement", "first_seen_at", "last_seen_at")
    readonly_fields = ("device_hash", "entitlement", "first_seen_at", "last_seen_at")

    @admin.display(description="Device hash")
    def short_hash(self, obj):
        return f"{obj.device_hash[:12]}…"


@admin.register(TrialAuditEvent)
class TrialAuditEventAdmin(admin.ModelAdmin):
    list_display = ("event_type", "entitlement", "user", "actor", "created_at")
    list_filter = ("event_type", "created_at")
    search_fields = ("user__username", "entitlement__account_links__user__username")
    readonly_fields = (
        "entitlement", "user", "actor", "event_type", "device_hash", "ip_hash", "details", "created_at",
    )

    def has_add_permission(self, request):
        return False
