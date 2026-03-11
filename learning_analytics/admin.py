from django.contrib import admin

from .models import (
    ProblemSkill,
    Skill,
    SkillPrerequisite,
    UserLearningPath,
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
