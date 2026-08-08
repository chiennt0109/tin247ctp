from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("problems", "0008_problem_difficulty_rating_fields")]

    operations = [
        migrations.AddField(
            model_name="testcase",
            name="is_sample",
            field=models.BooleanField(
                db_index=True,
                default=False,
                help_text="Chỉ các test được đánh dấu mới hiển thị cho thí sinh.",
                verbose_name="Test ví dụ",
            ),
        ),
    ]
