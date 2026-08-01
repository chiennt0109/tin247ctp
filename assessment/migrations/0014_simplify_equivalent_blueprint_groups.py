from django.db import migrations, models


def copy_existing_memberships(apps, schema_editor):
    ExamBlueprint = apps.get_model("assessment", "ExamBlueprint")
    ExamBlueprintGroup = apps.get_model("assessment", "ExamBlueprintGroup")
    through = ExamBlueprintGroup._meta.get_field("blueprints").remote_field.through
    for blueprint in ExamBlueprint.objects.exclude(equivalence_group_id=None):
        through.objects.get_or_create(
            examblueprintgroup_id=blueprint.equivalence_group_id,
            examblueprint_id=blueprint.pk,
        )


class Migration(migrations.Migration):
    dependencies = [("assessment", "0013_equivalent_blueprint_groups")]
    operations = [
        migrations.AddField(
            model_name="examblueprintgroup", name="exam_type",
            field=models.CharField(
                choices=[
                    ("PRACTICE", "Luyện tập"), ("REGULAR", "Kiểm tra thường xuyên"),
                    ("PERIODIC", "Kiểm tra định kỳ"), ("GRADUATION", "Thi thử tốt nghiệp"),
                    ("CUSTOM", "Tùy chỉnh"),
                ], default="GRADUATION", max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="examblueprintgroup", name="is_active",
            field=models.BooleanField(db_index=True, default=True),
        ),
        migrations.AddField(
            model_name="examblueprintgroup", name="selection_policy",
            field=models.CharField(
                choices=[("RANDOM_READY", "Chọn ngẫu nhiên trong các ma trận READY")],
                default="RANDOM_READY", max_length=32,
            ),
        ),
        migrations.AddField(
            model_name="examblueprintgroup", name="duration_tolerance_minutes",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="examblueprintgroup", name="blueprints",
            field=models.ManyToManyField(blank=True, related_name="equivalence_groups", to="assessment.examblueprint"),
        ),
        migrations.RunPython(copy_existing_memberships, migrations.RunPython.noop),
        migrations.RemoveField(model_name="examblueprint", name="equivalence_group"),
    ]
