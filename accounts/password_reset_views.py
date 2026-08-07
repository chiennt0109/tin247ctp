import hashlib

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.db import transaction
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import PasswordResetConfirmForm, PasswordResetRequestForm
from .models import PasswordResetRequest


GENERIC_MESSAGE = (
    "Yêu cầu của bạn đã được ghi nhận. Nếu thông tin tài khoản hợp lệ, "
    "quản trị viên sẽ xử lý yêu cầu."
)


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",", 1)[0] if forwarded else request.META.get("REMOTE_ADDR", "unknown")).strip()


def _rate_limited(request, identifier):
    ip_digest = hashlib.sha256(_client_ip(request).encode()).hexdigest()
    account_digest = hashlib.sha256(identifier.casefold().encode()).hexdigest()
    keys = ((f"password-reset:ip:{ip_digest}", 5), (f"password-reset:account:{account_digest}", 3))
    limited = False
    for key, limit in keys:
        count = cache.get(key, 0)
        if count >= limit:
            limited = True
        elif count == 0:
            cache.set(key, 1, timeout=3600)
        else:
            try:
                cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=3600)
    return limited


def password_reset_request(request):
    form = PasswordResetRequestForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"].strip()
        if not _rate_limited(request, identifier):
            user = get_user_model().objects.filter(
                Q(username__iexact=identifier) | Q(email__iexact=identifier)
            ).first()
            if user:
                PasswordResetRequest.objects.get_or_create(
                    user=user,
                    status=PasswordResetRequest.Status.PENDING,
                )
        messages.success(request, GENERIC_MESSAGE)
        return redirect("account_reset_password")
    return render(request, "account/password_reset.html", {"form": form})


@transaction.atomic
def password_reset_confirm(request):
    form = PasswordResetConfirmForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        identifier = form.cleaned_data["identifier"].strip()
        user = get_user_model().objects.filter(
            Q(username__iexact=identifier) | Q(email__iexact=identifier)
        ).first()
        reset_request = None
        if user:
            reset_request = PasswordResetRequest.objects.select_for_update().filter(
                user=user,
                status=PasswordResetRequest.Status.ISSUED,
                used_at__isnull=True,
            ).order_by("-handled_at").first()

        now = timezone.now()
        if reset_request and reset_request.expires_at and reset_request.expires_at <= now:
            reset_request.status = PasswordResetRequest.Status.EXPIRED
            reset_request.save(update_fields=("status",))
            reset_request = None

        if not reset_request or not reset_request.code_matches(form.cleaned_data["reset_code"]):
            form.add_error(None, "Thông tin hoặc mã đặt lại mật khẩu không hợp lệ.")
        else:
            try:
                validate_password(form.cleaned_data["new_password1"], user=user)
            except ValidationError as error:
                form.add_error("new_password1", error)
            else:
                user.set_password(form.cleaned_data["new_password1"])
                user.save(update_fields=("password",))
                reset_request.status = PasswordResetRequest.Status.COMPLETED
                reset_request.used_at = now
                reset_request.completed_at = now
                reset_request.save(update_fields=("status", "used_at", "completed_at"))
                messages.success(request, "Mật khẩu đã được đặt lại. Bạn có thể đăng nhập bằng mật khẩu mới.")
                return redirect("account_login")
    return render(request, "account/password_reset_confirm_code.html", {"form": form})
