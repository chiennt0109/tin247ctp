from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Skill(models.Model):
    LEVEL_BEGINNER = "Beginner"
    LEVEL_INTERMEDIATE = "Intermediate"
    LEVEL_ADVANCED = "Advanced"
    LEVEL_OLYMPIAD = "Olympiad"
    LEVEL_CHOICES = [
        (LEVEL_BEGINNER, "Beginner"),
        (LEVEL_INTERMEDIATE, "Intermediate"),
        (LEVEL_ADVANCED, "Advanced"),
        (LEVEL_OLYMPIAD, "Olympiad"),
    ]

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    category = models.CharField(max_length=80, default="Basic Programming")
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_BEGINNER)
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="children"
    )
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class SkillPrerequisite(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="prerequisites")
    prerequisite = models.ForeignKey(
        Skill, on_delete=models.CASCADE, related_name="required_for"
    )

    class Meta:
        unique_together = (("skill", "prerequisite"),)

    def __str__(self):
        return f"{self.prerequisite} -> {self.skill}"


class ProblemSkill(models.Model):
    problem = models.ForeignKey("problems.Problem", on_delete=models.CASCADE, related_name="problem_skills")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="problem_skills")
    weight = models.FloatField(default=1.0)

    class Meta:
        unique_together = (("problem", "skill"),)

    def __str__(self):
        return f"{self.problem.code} -> {self.skill.name}"


class UserSkill(models.Model):
    LEVEL_WEAK = "weak"
    LEVEL_BASIC = "basic"
    LEVEL_INTERMEDIATE = "intermediate"
    LEVEL_STRONG = "strong"

    LEVEL_CHOICES = [
        (LEVEL_WEAK, "Weak"),
        (LEVEL_BASIC, "Basic"),
        (LEVEL_INTERMEDIATE, "Intermediate"),
        (LEVEL_STRONG, "Strong"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_scores")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="user_scores")
    skill_score = models.FloatField(default=0.0)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default=LEVEL_WEAK)
    weakness_score = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (("user", "skill"),)
        indexes = [models.Index(fields=["user", "level"]), models.Index(fields=["user", "-weakness_score"])]


class UserSkillStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="skill_stats")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="user_skill_stats")
    attempted_problems = models.PositiveIntegerField(default=0)
    solved_problems = models.PositiveIntegerField(default=0)
    skill_score = models.FloatField(default=0.0)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (("user", "skill"),)


class UserTopicStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="topic_stats")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="topic_stats")
    attempted = models.PositiveIntegerField(default=0)
    solved = models.PositiveIntegerField(default=0)
    acceptance_rate = models.FloatField(default=0.0)
    tle_rate = models.FloatField(default=0.0)
    progress = models.FloatField(default=0.0)
    avg_exec_time = models.FloatField(default=0.0)
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = (("user", "skill"),)


class UserProblemStats(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="problem_stats")
    problem = models.ForeignKey("problems.Problem", on_delete=models.CASCADE, related_name="user_problem_stats")
    attempts = models.PositiveIntegerField(default=0)
    solved = models.BooleanField(default=False)
    wa_count = models.PositiveIntegerField(default=0)
    tle_count = models.PositiveIntegerField(default=0)
    re_count = models.PositiveIntegerField(default=0)
    best_exec_time = models.FloatField(default=0.0)
    first_attempt_at = models.DateTimeField(null=True, blank=True)
    last_submission_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("user", "problem"),)


class UserLearningPath(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="learning_path")
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="learning_paths")
    order = models.PositiveIntegerField()
    status = models.CharField(max_length=20, default="not_started")
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = (("user", "skill"),)
        ordering = ["order"]
