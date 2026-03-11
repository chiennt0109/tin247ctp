from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.db.models import DateTimeField, F, Max, Value
from django.db.models.functions import Coalesce, Greatest
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    ProblemSkill,
    Skill,
    SkillPrerequisite,
    UserLearningPath,
    LearningTrack,
    LearningTrackStep,
    UserProblemStats,
    UserSkill,
    UserSkillStats,
    UserTopicStats,
)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "level", "parent")
    list_filter = ("category", "level")
    search_fields = ("name", "description")


admin.site.register(SkillPrerequisite)
admin.site.register(ProblemSkill)
admin.site.register(UserSkill)
admin.site.register(UserSkillStats)
admin.site.register(UserTopicStats)
admin.site.register(UserProblemStats)
admin.site.register(UserLearningPath)
admin.site.register(LearningTrack)
admin.site.register(LearningTrackStep)


User = get_user_model()


class UserAnalyticsAdmin(UserAdmin):
    ACTIVITY_FALLBACK = Value("1970-01-01T00:00:00Z", output_field=DateTimeField())

    def learning_profile_link(self, obj):
        url = reverse("learning_analytics:user_learning_profile", kwargs={"user_id": obj.id})
        return format_html('<a class="button" href="{}">Learning Profile</a>', url)

    learning_profile_link.short_description = "Learning Profile"

    def learning_profile_button(self, obj):
        if not obj or not obj.pk:
            return "Save user first"
        url = reverse("learning_analytics:user_learning_profile", kwargs={"user_id": obj.id})
        return format_html(
            '<a class="button" style="padding:6px 12px;background:#2c7be5;color:white;border-radius:4px;text-decoration:none;" href="{}">View Learning Profile</a>',
            url,
        )

    learning_profile_button.short_description = "Learning Profile"


    def analytics_tools(self, obj=None):
        coverage_url = reverse("learning_analytics:skill_coverage")
        tracks_url = reverse("learning_analytics:training_tracks")
        return format_html(
            '<a class="button" href="{}" style="margin-right:8px;">Skill Coverage</a>'
            '<a class="button" href="{}">Training Tracks</a>',
            coverage_url,
            tracks_url,
        )

    analytics_tools.short_description = "Learning Analytics"

    list_display = UserAdmin.list_display + ("recent_activity", "learning_profile_link",)
    readonly_fields = UserAdmin.readonly_fields + ("learning_profile_button", "analytics_tools")


    @admin.display(description="Recent activity")
    def recent_activity(self, obj):
        return getattr(obj, "recent_activity_at", None)


    def get_queryset(self, request):
        qs = super().get_queryset(request).annotate(
            latest_submission_at=Max("submission__created_at"),
            latest_problem_submission_at=Max("problem_stats__last_submission_at"),
            latest_progress_at=Max("progress__last_submit"),
        )
        return qs.annotate(
            recent_activity_at=Greatest(
                Coalesce("last_login", self.ACTIVITY_FALLBACK),
                Coalesce("latest_submission_at", self.ACTIVITY_FALLBACK),
                Coalesce("latest_problem_submission_at", self.ACTIVITY_FALLBACK),
                Coalesce("latest_progress_at", self.ACTIVITY_FALLBACK),
            )
        ).order_by(F("recent_activity_at").desc(nulls_last=True), "username")

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        return fieldsets + (("Learning Analytics", {"fields": ("learning_profile_button", "analytics_tools")}),)


try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass
admin.site.register(User, UserAnalyticsAdmin)
