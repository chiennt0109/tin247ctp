from django.contrib import admin, messages
from django.shortcuts import render
from django.utils import timezone

from .models import PasswordResetRequest, RegistrationRequest, RegistrationSettings


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "status", "created_at", "reviewed_by")
    list_filter = ("status", "created_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("user", "created_at", "reviewed_at", "reviewed_by")
    actions = ("approve_selected", "reject_selected")

    @admin.display(description="Tên đăng nhập")
    def username(self, obj):
        return obj.user.username

    @admin.display(description="Email")
    def email(self, obj):
        return obj.user.email

    @admin.action(description="Phê duyệt các đăng ký đã chọn")
    def approve_selected(self, request, queryset):
        count = 0
        for registration in queryset.select_related("user"):
            registration.approve(request.user)
            count += 1
        self.message_user(request, f"Đã phê duyệt {count} tài khoản.", messages.SUCCESS)

    @admin.action(description="Từ chối các đăng ký đã chọn")
    def reject_selected(self, request, queryset):
        count = 0
        for registration in queryset.select_related("user"):
            registration.reject(request.user)
            count += 1
        self.message_user(request, f"Đã từ chối {count} tài khoản.", messages.SUCCESS)

    def has_add_permission(self, request):
        return False


@admin.register(RegistrationSettings)
class RegistrationSettingsAdmin(admin.ModelAdmin):
    list_display = ("auto_approve",)

    def has_add_permission(self, request):
        return not RegistrationSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ("username", "registered_email", "status", "requested_at", "expires_at", "handled_by")
    list_filter = ("status", "requested_at", "expires_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = (
        "user", "status", "requested_at", "handled_by", "handled_at",
        "expires_at", "used_at", "completed_at", "token_hash",
    )
    actions = ("issue_codes", "reject_requests")

    @admin.display(description="Tên đăng nhập")
    def username(self, obj):
        return obj.user.username

    @admin.display(description="Email đã đăng ký")
    def registered_email(self, obj):
        return obj.user.email

    @admin.action(description="Tạo mã đặt lại mật khẩu")
    def issue_codes(self, request, queryset):
        issued = []
        for reset_request in queryset.select_related("user"):
            if reset_request.status in (reset_request.Status.PENDING, reset_request.Status.ISSUED):
                issued.append({
                    "username": reset_request.user.username,
                    "email": reset_request.user.email,
                    "code": reset_request.issue(request.user),
                    "expires_at": reset_request.expires_at,
                })
        if not issued:
            self.message_user(request, "Không có yêu cầu phù hợp để cấp mã.", messages.WARNING)
            return None
        response = render(request, "admin/accounts/password_reset_codes.html", {"issued": issued})
        response["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response["Pragma"] = "no-cache"
        return response

    @admin.action(description="Từ chối yêu cầu đã chọn")
    def reject_requests(self, request, queryset):
        now = timezone.now()
        count = queryset.filter(status=PasswordResetRequest.Status.PENDING).update(
            status=PasswordResetRequest.Status.REJECTED,
            handled_by=request.user,
            handled_at=now,
        )
        self.message_user(request, f"Đã từ chối {count} yêu cầu.", messages.SUCCESS)

    def has_add_permission(self, request):
        return False
