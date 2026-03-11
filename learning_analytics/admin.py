from django.contrib import admin

from .models import (
    ProblemSkill,
    Skill,
    SkillPrerequisite,
    UserLearningPath,
    UserProblemStats,
    UserSkill,
    UserTopicStats,
)

admin.site.register(Skill)
admin.site.register(SkillPrerequisite)
admin.site.register(ProblemSkill)
admin.site.register(UserSkill)
admin.site.register(UserTopicStats)
admin.site.register(UserProblemStats)
admin.site.register(UserLearningPath)
