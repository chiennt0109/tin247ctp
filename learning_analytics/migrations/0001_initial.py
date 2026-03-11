from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("problems", "0007_checker_textchoices_refactor"),
    ]

    operations = [
        migrations.CreateModel(
            name="Skill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(max_length=120, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "parent",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="children", to="learning_analytics.skill"),
                ),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="ProblemSkill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("weight", models.FloatField(default=1.0)),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="problem_skills", to="problems.problem")),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="problem_skills", to="learning_analytics.skill")),
            ],
            options={"unique_together": {("problem", "skill")}},
        ),
        migrations.CreateModel(
            name="SkillPrerequisite",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("prerequisite", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="required_for", to="learning_analytics.skill")),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="prerequisites", to="learning_analytics.skill")),
            ],
            options={"unique_together": {("skill", "prerequisite")}},
        ),
        migrations.CreateModel(
            name="UserSkill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("skill_score", models.FloatField(default=0.0)),
                ("level", models.CharField(choices=[("weak", "Weak"), ("basic", "Basic"), ("intermediate", "Intermediate"), ("strong", "Strong")], default="weak", max_length=20)),
                ("weakness_score", models.FloatField(default=0.0)),
                ("last_updated", models.DateTimeField(default=django.utils.timezone.now)),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_scores", to="learning_analytics.skill")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="skill_scores", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [models.Index(fields=["user", "level"], name="learning_ana_user_id_2ca6c3_idx"), models.Index(fields=["user", "-weakness_score"], name="learning_ana_user_id_82aefd_idx")],
                "unique_together": {("user", "skill")},
            },
        ),
        migrations.CreateModel(
            name="UserTopicStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempted", models.PositiveIntegerField(default=0)),
                ("solved", models.PositiveIntegerField(default=0)),
                ("acceptance_rate", models.FloatField(default=0.0)),
                ("tle_rate", models.FloatField(default=0.0)),
                ("progress", models.FloatField(default=0.0)),
                ("avg_exec_time", models.FloatField(default=0.0)),
                ("last_updated", models.DateTimeField(default=django.utils.timezone.now)),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="topic_stats", to="learning_analytics.skill")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="topic_stats", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("user", "skill")}},
        ),
        migrations.CreateModel(
            name="UserProblemStats",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("attempts", models.PositiveIntegerField(default=0)),
                ("solved", models.BooleanField(default=False)),
                ("wa_count", models.PositiveIntegerField(default=0)),
                ("tle_count", models.PositiveIntegerField(default=0)),
                ("re_count", models.PositiveIntegerField(default=0)),
                ("best_exec_time", models.FloatField(default=0.0)),
                ("first_attempt_at", models.DateTimeField(blank=True, null=True)),
                ("last_submission_at", models.DateTimeField(blank=True, null=True)),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_problem_stats", to="problems.problem")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="problem_stats", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("user", "problem")}},
        ),
        migrations.CreateModel(
            name="UserLearningPath",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField()),
                ("status", models.CharField(default="not_started", max_length=20)),
                ("reason", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_paths", to="learning_analytics.skill")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="learning_path", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["order"], "unique_together": {("user", "skill")}},
        ),
    ]
