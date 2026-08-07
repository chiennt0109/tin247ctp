from django.contrib import admin, messages

from .models import RegistrationRequest, RegistrationSettings


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
