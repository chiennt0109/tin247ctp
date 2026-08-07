from django.conf import settings
from django.db import models, transaction
from django.utils import timezone


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
