from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems", "0007_checker_textchoices_refactor"),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="difficulty_level",
            field=models.CharField(default="Easy", max_length=20),
        ),
        migrations.AddField(
            model_name="problem",
            name="difficulty_rating",
            field=models.IntegerField(default=1200),
        ),
    ]
