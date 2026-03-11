from django.db.models.signals import post_save
from django.dispatch import receiver

from problems.models import Problem

from .difficulty_engine import DifficultyEngine
from .skill_detector import detect_and_assign


@receiver(post_save, sender=Problem)
def auto_detect_problem_skills(sender, instance, created, **kwargs):
    # realtime detection for both add/edit
    detect_and_assign(instance, min_score=2, refresh=False)

    # keep difficulty rating in sync when problem stats/content are saved
    DifficultyEngine().update_problem(instance)
