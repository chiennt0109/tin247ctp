from django.db import models

class Problem(models.Model):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=100)
    statement = models.TextField()
    time_limit = models.IntegerField(default=2)       # seconds
    memory_limit = models.IntegerField(default=256)   # MB

    def __str__(self):
        return f"{self.code} - {self.title}"

class TestCase(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    input_data = models.TextField()
    expected_output = models.TextField()
