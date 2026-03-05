# arena/admin.py
from django.contrib import admin
from .models import ArenaGame, ArenaRun, ArenaSubscription, ArenaProgress


@admin.register(ArenaGame)
class ArenaGameAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "order")
    list_editable = ("is_active", "order")
    search_fields = ("name", "slug")


@admin.register(ArenaRun)
class ArenaRunAdmin(admin.ModelAdmin):
    list_display = ("id", "game", "user", "language", "score", "steps", "status", "created_at")
    list_filter = ("game", "language", "status", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("created_at",)


@admin.register(ArenaSubscription)
class ArenaSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "tier", "is_active", "expiry")
    list_filter = ("tier", "is_active")
    search_fields = ("user__username", "user__email")


@admin.register(ArenaProgress)
class ArenaProgressAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "game",
        "best_score_egg",
        "best_score_chick",
        "best_score_teen",
        "egg_passed",
        "chick_passed",
        "teen_passed",
        "current_x",      # ? Thay dúng field có trong DB
        "current_y",
        "updated_at",
    )
    list_filter = ("game", "egg_passed", "chick_passed", "teen_passed")
    search_fields = ("user__username", "user__email")
