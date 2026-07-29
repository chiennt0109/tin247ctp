from django.contrib import admin

from assessment.models import (
    AssessmentAuditLog, BankQuestion, BankQuestionRevision, BankSourceFile,
    CurriculumNode, CurriculumOutcome, QuestionAsset, QuestionSyncLog,
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
