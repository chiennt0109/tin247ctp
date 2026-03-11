from django.apps import AppConfig


class LearningAnalyticsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "learning_analytics"
    verbose_name = "Learning Analytics"

    def ready(self):
        import learning_analytics.signals  # noqa: F401
