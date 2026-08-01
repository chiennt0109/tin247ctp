from django.db import migrations


GROUP_FIELDS = (
    "exam_type",
    "is_active",
    "selection_policy",
    "duration_tolerance_minutes",
)


def ensure_blueprint_group_schema(apps, schema_editor):
    """Repair databases where migration 0014 was recorded without its DDL."""
    Group = apps.get_model("assessment", "ExamBlueprintGroup")
    table = Group._meta.db_table
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        columns = {
            column.name
            for column in connection.introspection.get_table_description(cursor, table)
        }
    for field_name in GROUP_FIELDS:
        if field_name not in columns:
            schema_editor.add_field(Group, Group._meta.get_field(field_name))

    through = Group._meta.get_field("blueprints").remote_field.through
    if through._meta.db_table not in connection.introspection.table_names():
        schema_editor.create_model(through)


class Migration(migrations.Migration):
    dependencies = [("assessment", "0014_simplify_equivalent_blueprint_groups")]
    operations = [migrations.RunPython(ensure_blueprint_group_schema, migrations.RunPython.noop)]
