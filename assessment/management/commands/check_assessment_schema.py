from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

from assessment.models import ExamBlueprintGroup


REQUIRED_GROUP_COLUMNS = {
    "exam_type", "is_active", "selection_policy", "duration_tolerance_minutes",
}


class Command(BaseCommand):
    help = "Verify that deployed assessment migrations and blueprint-group columns exist"

    def handle(self, *args, **options):
        applied = set(
            MigrationRecorder(connection).migration_qs.filter(app="assessment")
            .values_list("name", flat=True)
        )
        table = ExamBlueprintGroup._meta.db_table
        tables = set(connection.introspection.table_names())
        columns = set()
        if table in tables:
            with connection.cursor() as cursor:
                columns = {
                    column.name
                    for column in connection.introspection.get_table_description(cursor, table)
                }
        missing_migrations = [
            name for name in (
                "0014_simplify_equivalent_blueprint_groups",
                "0015_verify_blueprint_group_schema",
            ) if name not in applied
        ]
        missing_columns = sorted(REQUIRED_GROUP_COLUMNS - columns)
        if missing_migrations or missing_columns:
            details = []
            if missing_migrations:
                details.append("migration chưa áp dụng: " + ", ".join(missing_migrations))
            if missing_columns:
                details.append("column còn thiếu: " + ", ".join(missing_columns))
            raise CommandError("Assessment schema chưa sẵn sàng; chạy `python manage.py migrate assessment`: " + "; ".join(details))
        self.stdout.write(self.style.SUCCESS("Assessment blueprint-group schema is ready."))
