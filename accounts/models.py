from django.conf import settings
from django.db import models, transaction
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
import secrets


class RegistrationSettings(models.Model):
    auto_approve = models.BooleanField(
        default=False,
        verbose_name="Tự động phê duyệt đăng ký mới",
        help_text="Tài khoản tạo sau khi bật tùy chọn này sẽ được kích hoạt ngay.",
    )

    class Meta:
        verbose_name = "Cài đặt phê duyệt"
        verbose_name_plural = "Cài đặt phê duyệt"

    @classmethod
    def auto_approval_enabled(cls):
        return cls.objects.filter(pk=1, auto_approve=True).exists()

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Phê duyệt tự động: " + ("Bật" if self.auto_approve else "Tắt")


class RegistrationRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Chờ phê duyệt"
        APPROVED = "approved", "Đã phê duyệt"
        REJECTED = "rejected", "Đã từ chối"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="registration_request",
        verbose_name="Tài khoản",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày đăng ký")
    reviewed_at = models.DateTimeField(null=True, blank=True, verbose_name="Ngày xử lý")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviewed_registrations",
        verbose_name="Người xử lý",
    )

    class Meta:
        ordering = ("-created_at",)
        verbose_name = "Đăng ký tài khoản"
        verbose_name_plural = "Quản lý đăng ký"

    def __str__(self):
        return f"{self.user.username} – {self.get_status_display()}"

    @transaction.atomic
    def approve(self, reviewer=None):
        self.user.is_active = True
        self.user.save(update_fields=("is_active",))
        self.status = self.Status.APPROVED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save(update_fields=("status", "reviewed_at", "reviewed_by"))

    @transaction.atomic
    def reject(self, reviewer=None):
        self.user.is_active = False
        self.user.save(update_fields=("is_active",))
        self.status = self.Status.REJECTED
        self.reviewed_at = timezone.now()
        self.reviewed_by = reviewer
        self.save(update_fields=("status", "reviewed_at", "reviewed_by"))


class PasswordResetRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Chờ xử lý"
        ISSUED = "issued", "Đã cấp mã"
        COMPLETED = "completed", "Đã hoàn tất"
        EXPIRED = "expired", "Đã hết hạn"
        REJECTED = "rejected", "Đã từ chối"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="manual_password_reset_requests",
        verbose_name="Tài khoản",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    requested_at = models.DateTimeField(auto_now_add=True, verbose_name="Ngày yêu cầu")
    handled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="handled_password_resets",
        verbose_name="Người xử lý",
    )
    handled_at = models.DateTimeField(null=True, blank=True, verbose_name="Ngày xử lý")
    token_hash = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name="Hết hạn lúc")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Sử dụng lúc")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Hoàn tất lúc")

    class Meta:
        ordering = ("-requested_at",)
        verbose_name = "Yêu cầu đặt lại mật khẩu"
        verbose_name_plural = "Quản lý đặt lại mật khẩu"
        constraints = [
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(status="pending"),
                name="one_pending_password_reset_per_user",
            ),
            models.UniqueConstraint(
                fields=("user",),
                condition=models.Q(status="issued"),
                name="one_issued_password_reset_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user.username} – {self.get_status_display()}"

    @staticmethod
    def normalize_code(code):
        return "".join(character for character in code.upper() if character.isalnum())

    @classmethod
    def generate_code(cls):
        alphabet = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"
        raw = "".join(secrets.choice(alphabet) for _ in range(12))
        return "-".join(raw[index:index + 4] for index in range(0, 12, 4))

    @transaction.atomic
    def issue(self, reviewer):
        now = timezone.now()
        type(self).objects.select_for_update().filter(
            user=self.user,
            status=self.Status.ISSUED,
        ).exclude(pk=self.pk).update(status=self.Status.EXPIRED)
        code = self.generate_code()
        self.status = self.Status.ISSUED
        self.token_hash = make_password(self.normalize_code(code))
        self.expires_at = now + timezone.timedelta(hours=24)
        self.handled_by = reviewer
        self.handled_at = now
        self.used_at = None
        self.completed_at = None
        self.save(update_fields=(
            "status", "token_hash", "expires_at", "handled_by", "handled_at",
            "used_at", "completed_at",
        ))
        return code

    def code_matches(self, code):
        return bool(self.token_hash) and check_password(self.normalize_code(code), self.token_hash)
