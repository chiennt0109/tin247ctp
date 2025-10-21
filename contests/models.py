from django.db import models
from django.contrib.auth.models import User
from problems.models import Problem

class Contest(models.Model):
    name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    problems = models.ManyToManyField(Problem)
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Participation(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    penalty = models.IntegerField(default=0)
    last_submit = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (('contest','user'),)
