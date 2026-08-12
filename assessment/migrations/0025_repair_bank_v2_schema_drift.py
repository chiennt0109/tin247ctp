"""Idempotently repair databases where 0024 lacks physical columns."""

from django.db import migrations


FIELD_NAMES = (
    "ai_component", "grad_ai_task", "grad_nls_task", "graduation_gate",
    "import_warnings", "nls_frame", "nls_level", "nls_primary",
)


def repair_missing_columns(apps, schema_editor):
    question = apps.get_model("assessment", "BankQuestion")
    table = question._meta.db_table
    with schema_editor.connection.cursor() as cursor:
        description = schema_editor.connection.introspection.get_table_description(cursor, table)
    existing = {column.name for column in description}
    for name in FIELD_NAMES:
        if name not in existing:
            schema_editor.add_field(question, question._meta.get_field(name))
            existing.add(name)


class Migration(migrations.Migration):
    dependencies = [("assessment", "0024_bank_v2_nls_ai_metadata")]
    operations = [migrations.RunPython(repair_missing_columns, migrations.RunPython.noop)]
