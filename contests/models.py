from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# ============================================================
# CONTEST
# ============================================================

class Contest(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    # Quan trọng: TRÁNH IMPORT VÒNG LẶP
    problems = models.ManyToManyField("problems.Problem")

    is_public = models.BooleanField(default=True)

    practice_time = models.PositiveIntegerField(
        default=10800,
        help_text="Thời gian Practice (giây)"
    )
    practice_open = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def status(self):
        now = timezone.now()
        if now < self.start_time:
            return "upcoming"
        if now > self.end_time:
            return "finished"
        return "running"

    @property
    def duration(self):
        if not self.start_time or not self.end_time:
            return None
        delta = self.end_time - self.start_time
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        return f"{hours}h {minutes}m"

    @property
    def practice_minutes(self):
        return self.practice_time // 60


# ============================================================
# SCOREBOARD PARTICIPATION
# ============================================================

class Participation(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    penalty = models.IntegerField(default=0)
    last_submit = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (("contest", "user"),)

    def __str__(self):
        return f"{self.user.username} @ {self.contest.name}"


# ============================================================
# PRACTICE SESSION
# ============================================================

class PracticeSession(models.Model):
    contest = models.ForeignKey(
        Contest, on_delete=models.CASCADE, related_name="practice_sessions"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="practice_sessions"
    )

    attempt = models.PositiveIntegerField(default=1)

    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)

    is_started = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    cancelled = models.BooleanField(default=False)

    score = models.FloatField(default=0)
    last_submit = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Practice #{self.attempt} – {self.user.username} – {self.contest.name}"

    @property
    def remaining_seconds(self):
        if not self.is_started or not self.start_time or not self.end_time:
            return None
        if self.is_locked:
            return 0
        now = timezone.now()
        return max(0, int((self.end_time - now).total_seconds()))


# ============================================================
# 🎯 CONTEST EDITORIAL ACCESS — FIXED
# ============================================================

class ContestEditorialAccess(models.Model):

    MODE_CONTEST_HIDDEN = "contest_hidden"
    MODE_SHOW_AFTER_CONTEST = "show_after_contest"
    MODE_SHOW_ONLY_FREE = "show_only_free"
    MODE_SHOW_PAID_ONLY = "show_paid_only"

    MODE_CHOICES = [
        (MODE_CONTEST_HIDDEN, "Hide during contest"),
        (MODE_SHOW_AFTER_CONTEST, "Show after contest ends"),
        (MODE_SHOW_ONLY_FREE, "Show free editorial during contest"),
        (MODE_SHOW_PAID_ONLY, "Paid-only during contest"),
    ]

    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name="editorial_access_rules"
    )
    problem = models.ForeignKey(
        "problems.Problem",
        on_delete=models.CASCADE,
        related_name="contest_editorial_rules"
    )

    mode = models.CharField(max_length=32, choices=MODE_CHOICES, default=MODE_CONTEST_HIDDEN)

    class Meta:
        unique_together = ("contest", "problem")

    def __str__(self):
        return f"{self.contest} - {self.problem.code} ({self.mode})"



def save(self, *args, **kwargs):
    super().save(*args, **kwargs)

    # AUTO CREATE RULES FOR PROBLEMS IN THIS CONTEST
    from contests.models import ContestEditorialAccess

    # Duyệt toàn bộ bài đã gán vào contest
    for p in self.problems.all():
        ContestEditorialAccess.objects.get_or_create(
            contest=self,
            problem=p,
            defaults={"mode": ContestEditorialAccess.MODE_CONTEST_HIDDEN}
        )
