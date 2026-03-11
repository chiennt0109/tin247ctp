from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning_analytics", "0003_learningtrack_learningtrackstep"),
    ]

    operations = [
        migrations.AddField(
            model_name="userskillstats",
            name="attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="userskillstats",
            name="last_practiced",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userskillstats",
            name="mastery_score",
            field=models.FloatField(default=0.0),
        ),
        migrations.AddField(
            model_name="userskillstats",
            name="successes",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
