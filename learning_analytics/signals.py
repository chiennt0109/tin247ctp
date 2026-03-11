from django.db.models.signals import post_save
from django.dispatch import receiver

from problems.models import Problem

from .models import ProblemSkill
from .difficulty_engine import DifficultyEngine
from .skill_detector import detect_skills


@receiver(post_save, sender=Problem)
def auto_detect_problem_skills(sender, instance, created, **kwargs):
    skills = detect_skills(instance)
    for skill in skills:
        ProblemSkill.objects.get_or_create(problem=instance, skill=skill)

    # keep difficulty rating in sync when problem stats/content are saved
    DifficultyEngine().update_problem(instance)
