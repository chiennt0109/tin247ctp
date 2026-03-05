# arena/models.py
from django.db import models
from django.contrib.auth import get_user_model

from django.contrib.auth.models import User
#from .models_game import ArenaGame   

User = get_user_model()


class ArenaGame(models.Model):
    """
    Danh sách game trong Arena (Snake, Robot Step, ...).
    """
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "id"]

    def __str__(self):
        return self.name


class ArenaSubscription(models.Model):
    """
    Dùng cho paywall sau này: user phải trả phí mới dùng được.
    Hiện tại chưa bật, nhưng tạo sẵn model cho tương lai.
    """
    TIER_CHOICES = [
        ("free", "Free"),
        ("pro", "Pro"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="arena_subscription",
    )
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default="free")
    is_active = models.BooleanField(default=False)
    expiry = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user} ({self.tier})"

    @property
    def can_play(self) -> bool:
        if self.user.is_superuser or self.user.is_staff:
            return True
        if not self.is_active:
            return False
        if self.expiry is None:
            return True
        from django.utils import timezone
        return self.expiry >= timezone.now()


class ArenaRun(models.Model):
    """
    Một lần chạy bot trong game.
    Dùng chung cho Snake Lite, Robot Step, và các game khác.
    """
    LANG_CPP = "cpp"
    LANG_PY = "py"

    LANG_CHOICES = [
        (LANG_CPP, "C++"),
        (LANG_PY, "Python"),
    ]

    game = models.ForeignKey(
        ArenaGame,
        on_delete=models.CASCADE,
        related_name="runs",
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="arena_runs",
    )
    language = models.CharField(max_length=10, choices=LANG_CHOICES)
    source_code = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    score = models.IntegerField(default=0)
    steps = models.IntegerField(default=0)
    status = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    replay_json = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.game.slug} run #{self.id}"




class ArenaProgress(models.Model):
    LEVEL_EGG = "egg"
    LEVEL_CHICK = "chick"
    LEVEL_TEEN = "teen"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(ArenaGame, on_delete=models.CASCADE)

    best_score_egg = models.IntegerField(default=0)
    best_score_chick = models.IntegerField(default=0)
    best_score_teen = models.IntegerField(default=0)

    egg_passed = models.BooleanField(default=False)
    chick_passed = models.BooleanField(default=False)
    teen_passed = models.BooleanField(default=False)

    # ⭐ STATEFUL CORE
    current_x = models.IntegerField(default=5)
    current_y = models.IntegerField(default=5)

    updated_at = models.DateTimeField(auto_now=True)

    def update_after_run(self, level, score, pass_threshold):
        if level == self.LEVEL_EGG:
            if score > self.best_score_egg:
                self.best_score_egg = score
            if score >= pass_threshold:
                self.egg_passed = True

        elif level == self.LEVEL_CHICK:
            if score > self.best_score_chick:
                self.best_score_chick = score
            if score >= pass_threshold:
                self.chick_passed = True

        elif level == self.LEVEL_TEEN:
            if score > self.best_score_teen:
                self.best_score_teen = score
            if score >= pass_threshold:
                self.teen_passed = True

        self.save()

    def reset_robot(self):
        self.current_x = 5
        self.current_y = 5
        self.save()
