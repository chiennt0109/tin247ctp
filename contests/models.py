from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from problems.models import Problem

class Contest(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    problems = models.ManyToManyField(Problem)
    is_public = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    @property
    def status(self):
        """Trạng thái tự động: upcoming / running / finished"""
        now = timezone.now()
        if self.start_time > now:
            return "upcoming"
        elif self.end_time < now:
            return "finished"
        else:
            return "running"

    @property
    def duration(self):
        """Thời lượng (giờ:phút)"""
        if not self.end_time or not self.start_time:
            return None
        delta = self.end_time - self.start_time
        hours, remainder = divmod(delta.total_seconds(), 3600)
        minutes = remainder // 60
        return f"{int(hours)}h {int(minutes)}m"

class Participation(models.Model):
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    score = models.FloatField(default=0)
    penalty = models.IntegerField(default=0)
    last_submit = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = (('contest', 'user'),)
