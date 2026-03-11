from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ("learning_analytics", "0002_skill_metadata_and_user_skill_stats"),
        ("problems", "0007_checker_textchoices_refactor"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearningTrack",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("track_name", models.CharField(max_length=120, unique=True)),
                ("category", models.CharField(max_length=80)),
                ("updated_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={"ordering": ["track_name"]},
        ),
        migrations.CreateModel(
            name="LearningTrackStep",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("order", models.PositiveIntegerField()),
                ("difficulty", models.CharField(blank=True, default="", max_length=20)),
                ("problem", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="learning_track_steps", to="problems.problem")),
                ("skill", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="track_steps", to="learning_analytics.skill")),
                ("track", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="steps", to="learning_analytics.learningtrack")),
            ],
            options={"ordering": ["order"], "unique_together": {("track", "order")}},
        ),
    ]
