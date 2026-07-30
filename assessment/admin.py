from django.contrib import admin

from assessment.models import (
    AssessmentAuditLog, AttemptAnswer, BankQuestion, BankQuestionRevision, BankSourceFile,
    BlueprintSection, BlueprintSlot, BlueprintVersion, CurriculumNode, CurriculumOutcome,
    ExamAttempt, ExamBlueprint, ExamParticipant, ExamSession, GeneratedExam, GeneratedExamQuestion,
    QuestionAsset, QuestionSyncLog, ScoringRule, ScoringScheme, ScoringSchemeVersion,
)


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
    readonly_fields = ("validation_report", "approved_at", "created_at")

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_locked) and super().has_change_permission(request, obj)


@admin.register(ExamBlueprint)
class ExamBlueprintAdmin(admin.ModelAdmin):
    list_display = ("name", "exam_type", "grade", "semester", "status", "updated_at")
    list_filter = ("status", "exam_type", "grade", "semester")
    search_fields = ("name", "subject")
    list_select_related = ("created_by", "approved_by")


class ScoringRuleInline(admin.TabularInline):
    model = ScoringRule
    extra = 0

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_locked) and super().has_change_permission(request, obj)


@admin.register(ScoringSchemeVersion)
class ScoringSchemeVersionAdmin(admin.ModelAdmin):
    list_display = ("scheme", "version", "total_score", "rounding_digits", "is_locked")
    list_filter = ("is_locked",)
    list_select_related = ("scheme", "created_by")
    inlines = (ScoringRuleInline,)

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.is_locked) and super().has_change_permission(request, obj)


@admin.register(ScoringScheme)
class ScoringSchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "is_default", "created_by", "created_at")
    search_fields = ("name",)
    list_select_related = ("created_by",)


class ExamParticipantInline(admin.TabularInline):
    model = ExamParticipant
    extra = 0
    autocomplete_fields = ("user",)


class ExamAttemptInline(admin.TabularInline):
    model = ExamAttempt
    extra = 0
    can_delete = False
    fields = ("user", "attempt_number", "status", "generated_exam", "started_at", "expires_at")
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ExamSession)
class ExamSessionAdmin(admin.ModelAdmin):
    list_display = (
        "name", "exam_type", "generation_mode", "opens_at", "closes_at", "status",
    )
    list_filter = ("status", "exam_type", "generation_mode", "score_release_mode", "answer_release_mode")
    search_fields = ("name", "slug")
    list_select_related = ("blueprint_version", "scoring_version", "created_by")
    filter_horizontal = ("access_groups",)
    inlines = (ExamParticipantInline, ExamAttemptInline)

    def has_change_permission(self, request, obj=None):
        return not (obj and obj.status != ExamSession.Status.DRAFT) and super().has_change_permission(request, obj)


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
    list_display = ("code", "purpose", "session", "total_score", "exam_hash", "is_locked", "generated_at")
    search_fields = ("code", "session__name", "exam_hash")
    list_filter = ("purpose", "is_locked", "session__exam_type")
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
