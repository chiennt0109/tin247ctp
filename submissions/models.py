from django.db import models
from django.contrib.auth.models import User
from problems.models import Problem

LANG_CHOICES = [
    ('cpp', 'C++'),
    ('python', 'Python'),
    ('pypy', 'PyPy'),
    ('java', 'Java'),
]

class Submission(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    language = models.CharField(max_length=10, choices=LANG_CHOICES)
    source_code = models.TextField()
    verdict = models.CharField(max_length=30, default='Pending')
    exec_time = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} → {self.problem.code} [{self.verdict}]"
