from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contests", "0006_alter_contest_practice_time_contesteditorialaccess"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="contest",
            name="allowed_users",
            field=models.ManyToManyField(
                blank=True,
                help_text=(
                    "Để trống: tất cả tài khoản đều nhìn thấy. Khi chọn người dùng: "
                    "chỉ các tài khoản đã chọn mới nhìn thấy contest."
                ),
                related_name="visible_contests",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
