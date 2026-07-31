from django.db import migrations, models
import django.db.models.deletion


def remove_legacy_rows(apps, schema_editor):
    ExamAttempt = apps.get_model("assessment", "ExamAttempt")
    GeneratedExam = apps.get_model("assessment", "GeneratedExam")

    # An attempt without its one-to-one exam and an exam without an attempt
    # cannot belong to the new architecture. Keep every complete attempt,
    # blueprint, bank row and session (including historically demo-labelled rows).
    ExamAttempt.objects.filter(generated_exam__isnull=True).delete()
    GeneratedExam.objects.filter(attempt__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [("assessment", "0010_phase6_results_analytics")]

    operations = [
        migrations.RunPython(remove_legacy_rows, migrations.RunPython.noop),
        migrations.DeleteModel(name="ExamParticipant"),
        migrations.RemoveConstraint(
            model_name="generatedexam", name="assessment_generated_exam_valid_purpose",
        ),
        migrations.RemoveField(model_name="generatedexam", name="purpose"),
        migrations.RemoveField(model_name="generatedexam", name="expires_at"),
        migrations.RemoveField(model_name="examsession", name="generation_mode"),
        migrations.RemoveField(model_name="examsession", name="code_count"),
        migrations.RemoveField(model_name="examsession", name="demo_key"),
        migrations.RemoveField(model_name="examsession", name="is_demo"),
        migrations.RemoveField(model_name="examblueprint", name="demo_key"),
        migrations.RemoveField(model_name="examblueprint", name="is_demo"),
        migrations.RemoveField(model_name="scoringscheme", name="demo_key"),
        migrations.RemoveField(model_name="scoringscheme", name="is_demo"),
        migrations.AlterField(
            model_name="examattempt", name="generated_exam",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="attempt", to="assessment.generatedexam",
            ),
        ),
        migrations.AlterField(
            model_name="examsession", name="access_mode",
            field=models.CharField(
                choices=[
                    ("ALL_USERS", "Mọi tài khoản"),
                    ("SELECTED_GROUPS", "Nhóm được chọn"),
                    ("SELECTED_GRADES", "Khối được chọn"),
                ], default="ALL_USERS", max_length=32,
            ),
        ),
        migrations.AlterModelOptions(
            name="generatedexam", options={"ordering": ("session", "code")},
        ),
        migrations.AlterModelOptions(
            name="assessmentauditlog",
            options={
                "ordering": ("-created_at",),
                "permissions": [
                    ("sync_bank", "Can synchronize the assessment bank"),
                    ("view_dashboard", "Can view assessment dashboard"),
                    ("view_audit_log", "Can view assessment audit log"),
                    ("manage_blueprint", "Can manage assessment blueprints"),
                    ("approve_blueprint", "Can approve assessment blueprints"),
                    ("manage_scoring", "Can manage assessment scoring"),
                    ("view_results", "Can view assessment results"),
                    ("release_results", "Can release assessment results"),
                    ("release_answers", "Can release assessment answers"),
                    ("manage_access", "Can manage assessment access"),
                    ("invalidate_attempt", "Can invalidate assessment attempts"),
                    ("regrade_attempts", "Can regrade assessment attempts"),
                ],
            },
        ),
    ]
