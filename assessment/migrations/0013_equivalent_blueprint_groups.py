import django.db.models.deletion
from django.db import migrations, models


def backfill_blueprint_metadata_and_attempts(apps, schema_editor):
    ExamBlueprint = apps.get_model("assessment", "ExamBlueprint")
    ExamAttempt = apps.get_model("assessment", "ExamAttempt")
    for blueprint in ExamBlueprint.objects.all():
        version = blueprint.versions.order_by("-version").first()
        if version:
            blueprint.total_questions = version.expected_question_count
            blueprint.total_score = version.expected_total_score
            blueprint.duration_minutes = version.duration_minutes
            blueprint.is_locked = version.is_locked
            blueprint.is_ready = version.is_locked and bool(version.validation_report.get("valid"))
            blueprint.save(update_fields=(
                "total_questions", "total_score", "duration_minutes", "is_locked", "is_ready",
            ))
    for attempt in ExamAttempt.objects.select_related("generated_exam__blueprint_version"):
        version = attempt.generated_exam.blueprint_version
        attempt.blueprint_id = version.blueprint_id
        attempt.blueprint_version_id = version.pk
        attempt.save(update_fields=("blueprint", "blueprint_version"))


class Migration(migrations.Migration):
    dependencies = [("assessment", "0012_rebind_graduation_mock_session")]
    operations = [
        migrations.CreateModel(
            name="ExamBlueprintGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("code", models.SlugField(max_length=160, unique=True)),
                ("cognitive_tolerance", models.DecimalField(decimal_places=3, default="0.100", max_digits=5)),
                ("description", models.TextField(blank=True)),
            ],
        ),
        migrations.AddField(model_name="examblueprint", name="difficulty_profile", field=models.JSONField(blank=True, default=dict)),
        migrations.AddField(model_name="examblueprint", name="duration_minutes", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="examblueprint", name="is_locked", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="examblueprint", name="is_ready", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="examblueprint", name="total_questions", field=models.PositiveIntegerField(default=0)),
        migrations.AddField(model_name="examblueprint", name="total_score", field=models.DecimalField(decimal_places=3, default=0, max_digits=8)),
        migrations.AddField(
            model_name="examblueprint", name="equivalence_group",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="blueprints", to="assessment.examblueprintgroup"),
        ),
        migrations.AddField(
            model_name="examsession", name="blueprint_group",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="exam_sessions", to="assessment.examblueprintgroup"),
        ),
        migrations.AddField(
            model_name="examattempt", name="blueprint",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="attempts", to="assessment.examblueprint"),
        ),
        migrations.AddField(
            model_name="examattempt", name="blueprint_version",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="attempts", to="assessment.blueprintversion"),
        ),
        migrations.RunPython(backfill_blueprint_metadata_and_attempts, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="examattempt", name="blueprint",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attempts", to="assessment.examblueprint"),
        ),
        migrations.AlterField(
            model_name="examattempt", name="blueprint_version",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="attempts", to="assessment.blueprintversion"),
        ),
    ]
