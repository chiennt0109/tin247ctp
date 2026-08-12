from django.apps import AppConfig

class SubmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'submissions'

    # Schema changes belong exclusively in Django migrations.  In particular,
    # AppConfig.ready() runs for check, makemigrations, workers and web startup;
    # querying or altering the database here made every management command emit
    # an apps-not-ready warning and could race with migrate.
