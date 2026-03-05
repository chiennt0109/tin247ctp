from django.db import models

class Problem(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=100)
    statement = models.TextField()
    input_spec = models.TextField(blank=True)
    output_spec = models.TextField(blank=True)
    sample_input = models.TextField(blank=True)
    sample_output = models.TextField(blank=True)
    time_limit = models.FloatField(default=1.0)
    memory_limit = models.IntegerField(default=256)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code}: {self.title}"


class Submission(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    username = models.CharField(max_length=50)
    language = models.CharField(max_length=20)
    code = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="Pending")
    result = models.TextField(blank=True)

    def __str__(self):
        return f"{self.username} → {self.problem.code} ({self.status})"
