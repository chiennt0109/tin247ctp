from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="PasswordResetRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("pending", "Chờ xử lý"), ("issued", "Đã cấp mã"), ("completed", "Đã hoàn tất"), ("expired", "Đã hết hạn"), ("rejected", "Đã từ chối")], default="pending", max_length=16)),
                ("requested_at", models.DateTimeField(auto_now_add=True, verbose_name="Ngày yêu cầu")),
                ("handled_at", models.DateTimeField(blank=True, null=True, verbose_name="Ngày xử lý")),
                ("token_hash", models.CharField(blank=True, max_length=128)),
                ("expires_at", models.DateTimeField(blank=True, null=True, verbose_name="Hết hạn lúc")),
                ("used_at", models.DateTimeField(blank=True, null=True, verbose_name="Sử dụng lúc")),
                ("completed_at", models.DateTimeField(blank=True, null=True, verbose_name="Hoàn tất lúc")),
                ("handled_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="handled_password_resets", to=settings.AUTH_USER_MODEL, verbose_name="Người xử lý")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="manual_password_reset_requests", to=settings.AUTH_USER_MODEL, verbose_name="Tài khoản")),
            ],
            options={"verbose_name": "Yêu cầu đặt lại mật khẩu", "verbose_name_plural": "Quản lý đặt lại mật khẩu", "ordering": ("-requested_at",)},
        ),
        migrations.AddConstraint(
            model_name="passwordresetrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "pending")), fields=("user",), name="one_pending_password_reset_per_user"),
        ),
        migrations.AddConstraint(
            model_name="passwordresetrequest",
            constraint=models.UniqueConstraint(condition=models.Q(("status", "issued")), fields=("user",), name="one_issued_password_reset_per_user"),
        ),
    ]
