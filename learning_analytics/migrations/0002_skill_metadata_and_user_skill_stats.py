from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("learning_analytics", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="skill",
            name="category",
            field=models.CharField(default="Basic Programming", max_length=80),
        ),
        migrations.AddField(
            model_name="skill",
            name="level",
            field=models.CharField(
                choices=[
                    ("Beginner", "Beginner"),
                    ("Intermediate", "Intermediate"),
                    ("Advanced", "Advanced"),
                    ("Olympiad", "Olympiad"),
                ],
                default="Beginner",
                max_length=20,
            ),
        ),
        migrations.AlterModelOptions(
            name="skill",
            options={"ordering": ["category", "name"]},
        ),
        migrations.CreateModel(
            name="UserSkillStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempted_problems", models.PositiveIntegerField(default=0)),
                ("solved_problems", models.PositiveIntegerField(default=0)),
                ("skill_score", models.FloatField(default=0.0)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_skill_stats", to="learning_analytics.skill")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="skill_stats", to="auth.user")),
            ],
            options={"unique_together": {("user", "skill")}},
        ),
    ]
