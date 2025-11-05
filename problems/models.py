# path: problems/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone  # ✅ Thêm dòng này để dùng timezone.now


class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name


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
    tags = models.ManyToManyField(Tag, blank=True)
    has_editorial = models.BooleanField(default=False)
    ai_supported = models.BooleanField(default=False)
    ac_count = models.IntegerField(default=0)
    submission_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.now)  # ✅ Giữ duy nhất dòng này

    def __str__(self):
        return f"{self.code} - {self.title}"

    def success_rate(self):
        if self.submission_count == 0:
            return 0
        return round(100 * self.ac_count / self.submission_count, 2)


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
