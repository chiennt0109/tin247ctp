# path: problems/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone  # ✅ Thêm dòng này để dùng timezone.now




class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name




class CheckerType(models.TextChoices):
    NONE = "none", "None"
    CUSTOM = "custom", "Custom Checker"
    EULER_PATH = "euler_path", "Euler Path"
    PERMUTATION = "permutation", "Permutation"
    MATCHING = "matching", "Matching"
    GRAPH_PATH = "graph_path", "Graph Path"
    GRID = "grid", "Grid Construction"
    SET_COMPARE = "set_compare", "Set Compare"
    FLOAT_TOLERANCE = "float_tolerance", "Numeric Tolerance"
    PERMUTATION_CONSTRAINTS = "permutation_constraints", "Permutation With Constraints"
    ASSIGNMENT = "assignment", "Assignment"
    CONSTRUCTIVE = "constructive", "Constructive"


class Problem(models.Model):
    DIFFICULTY_CHOICES = [
        ('Easy', 'Easy'),
        ('Medium', 'Medium'),
        ('Hard', 'Hard'),
    ]

    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=150)
    statement = models.TextField()
    time_limit = models.IntegerField(default=2)       # seconds
    memory_limit = models.IntegerField(default=256)   # MB
    difficulty = models.CharField(max_length=10, choices=DIFFICULTY_CHOICES, default='Easy')
    difficulty_rating = models.IntegerField(default=1200)
    difficulty_level = models.CharField(max_length=20, default="Easy")
    tags = models.ManyToManyField(Tag, blank=True)
    has_editorial = models.BooleanField(default=False)
    ai_supported = models.BooleanField(default=False)
    ac_count = models.IntegerField(default=0)
    submission_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)  # ✅ Giữ duy nhất dòng này
    checker = models.CharField(max_length=50, choices=CheckerType.choices, default=CheckerType.NONE)
    checker_file = models.CharField(max_length=255, blank=True, default="")
    checker_config = models.TextField(blank=True, default="")
    
    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.title}"

    def success_rate(self):
        if self.submission_count == 0:
            return 0
        return round(100 * self.ac_count / self.submission_count, 2)
    # Update Dificult
    def auto_adjust_difficulty(self):
        """
        Điều chỉnh difficulty dựa trên tỷ lệ AC.
        """
        if self.submission_count == 0:
            self.difficulty = "Easy"
            return
    
        rate = self.ac_count / self.submission_count * 100
    
        if rate >= 70:
            self.difficulty = "Easy"
        elif rate >= 40:
            self.difficulty = "Medium"
        else:
            self.difficulty = "Hard"



class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    input_data = models.TextField()
    expected_output = models.TextField()

    def __str__(self):
        return f"TestCase for {self.problem.code}"


class UserProgress(models.Model):
    STATUS_CHOICES = [
        ("not_started", "Chưa bắt đầu"),
        ("in_progress", "Đang làm"),
        ("solved", "Đã AC"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="progress")
    problem = models.ForeignKey("Problem", on_delete=models.CASCADE, related_name="user_progress")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="not_started")
    attempts = models.PositiveIntegerField(default=0)
    best_score = models.FloatField(default=0)
    last_submit = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "problem")
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["problem"]),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.problem.code} ({self.status})"


# ============================================================
# 📘 EDITORIAL SYSTEM — SAFE VERSION (NO FIELD OVERRIDE)
# ============================================================

class ProblemEditorial(models.Model):
    ACCESS_FREE = "free"
    ACCESS_PAID = "paid"
    ACCESS_HIDDEN = "hidden"
    ACCESS_CONTEST_ONLY = "contest_only"

    ACCESS_CHOICES = [
        (ACCESS_FREE, "Free"),
        (ACCESS_PAID, "Paid"),
        (ACCESS_HIDDEN, "Hidden"),
        (ACCESS_CONTEST_ONLY, "Only after contest"),
    ]

    problem = models.OneToOneField(
        Problem,
        on_delete=models.CASCADE,
        related_name="editorial_meta"
    )
    content = models.TextField(blank=True, null=True)
    access_mode = models.CharField(
        max_length=20,
        choices=ACCESS_CHOICES,
        default=ACCESS_HIDDEN
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Editorial for {self.problem.code}"


class EditorialPurchase(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "problem")

    def __str__(self):
        return f"{self.user.username} purchased {self.problem.code}"


# ============================================================
# 🔄 SIGNAL: Đồng bộ Problem.has_editorial khi lưu editorial
# ============================================================
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

@receiver(post_save, sender=ProblemEditorial)
def update_has_editorial_on_save(sender, instance, **kwargs):
    problem = instance.problem
    has = bool(instance.content and instance.content.strip())
    if problem.has_editorial != has:
        problem.has_editorial = has
        problem.save(update_fields=["has_editorial"])


@receiver(post_delete, sender=ProblemEditorial)
def update_has_editorial_on_delete(sender, instance, **kwargs):
    problem = instance.problem
    if problem.has_editorial:
        problem.has_editorial = False
        problem.save(update_fields=["has_editorial"])

