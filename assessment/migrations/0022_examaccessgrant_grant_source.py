from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0021_remove_examusagerecord_trial_entitlement_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="examaccessgrant",
            name="grant_source",
            field=models.CharField(
                choices=[("ADMIN", "Quản trị viên"), ("AUTO_TRIAL", "Dùng thử tự động")],
                default="ADMIN",
                help_text="Nguồn tạo quyền; không tham gia tính hoặc giới hạn số lượt.",
                max_length=16,
            ),
        ),
    ]
