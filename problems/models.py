# path: problems/models.py
from django.db import models
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
