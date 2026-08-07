import hashlib
import hmac
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from assessment.models import (
    ExamUsageRecord, TrialAccountLink, TrialAuditEvent, TrialDevice, TrialEntitlement,
)

logger = logging.getLogger(__name__)
COOKIE_NAME = "trial_device_id"


def new_device_id():
    return str(uuid.uuid4())


def _hash_signal(value):
    if not value:
        return ""
    return hmac.new(settings.SECRET_KEY.encode(), str(value).encode(), hashlib.sha256).hexdigest()


def request_device_id(request):
    value = request.COOKIES.get(COOKIE_NAME, "")
    try:
        return str(uuid.UUID(value))
    except (ValueError, TypeError, AttributeError):
        return getattr(request, "trial_device_id", None) or new_device_id()


def request_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return (forwarded.split(",", 1)[0].strip() if forwarded else request.META.get("REMOTE_ADDR", ""))


def _limit(name, default):
    return int(getattr(settings, name, default))


@transaction.atomic
def provision_signup_trial(user, request):
    """Link a signup to a shared entitlement; IP is only a risk signal."""
    if not getattr(settings, "GENERAL_IT_TRIAL_ENABLED", True):
        return None
    existing = TrialAccountLink.objects.select_related("entitlement").filter(user=user).first()
    if existing:
        return existing.entitlement

    now = timezone.now()
    device_hash = _hash_signal(request_device_id(request))
    ip_hash = _hash_signal(request_ip(request))
    device = TrialDevice.objects.select_for_update().select_related("entitlement").filter(
        device_hash=device_hash,
    ).first()
    if device:
        entitlement = device.entitlement
        TrialAccountLink.objects.create(user=user, entitlement=entitlement)
        TrialAuditEvent.objects.create(
            entitlement=entitlement, user=user, event_type="ACCOUNT_LINKED_EXISTING_DEVICE",
            device_hash=device_hash, ip_hash=ip_hash,
        )
        device.save(update_fields=("last_seen_at",))
        return entitlement

    day = now - timedelta(days=1)
    month = now - timedelta(days=30)
    hour = now - timedelta(hours=1)
    ip_hour = TrialAuditEvent.objects.filter(ip_hash=ip_hash, event_type__startswith="SIGNUP", created_at__gte=hour).count()
    ip_day = TrialAuditEvent.objects.filter(ip_hash=ip_hash, event_type__startswith="SIGNUP", created_at__gte=day).count()
    device_day = TrialAuditEvent.objects.filter(device_hash=device_hash, event_type__startswith="SIGNUP", created_at__gte=day).count()
    device_month = TrialAuditEvent.objects.filter(device_hash=device_hash, event_type__startswith="SIGNUP", created_at__gte=month).count()
    review = (
        ip_hour >= _limit("TRIAL_SIGNUP_IP_LIMIT_HOUR", 5)
        or ip_day >= _limit("TRIAL_SIGNUP_IP_LIMIT_DAY", 20)
        or device_day >= _limit("TRIAL_SIGNUP_DEVICE_LIMIT_DAY", 2)
        or device_month >= _limit("TRIAL_SIGNUP_DEVICE_LIMIT_30D", 5)
    )
    entitlement = TrialEntitlement.objects.create(
        quota_total=_limit("GENERAL_IT_TRIAL_QUOTA", 3),
        status=(TrialEntitlement.Status.REVIEW_REQUIRED if review else TrialEntitlement.Status.ACTIVE),
    )
    try:
        with transaction.atomic():
            TrialDevice.objects.create(entitlement=entitlement, device_hash=device_hash)
    except IntegrityError:
        # Two simultaneous signups carrying the same cookie converge on the
        # database-unique device row instead of creating two allowances.
        shared = TrialDevice.objects.select_related("entitlement").get(device_hash=device_hash)
        entitlement.delete()
        entitlement = shared.entitlement
    TrialAccountLink.objects.create(user=user, entitlement=entitlement)
    TrialAuditEvent.objects.create(
        entitlement=entitlement, user=user,
        event_type="SIGNUP_REVIEW_REQUIRED" if review else "SIGNUP_GRANTED",
        device_hash=device_hash, ip_hash=ip_hash,
        details={"ip_hour": ip_hour, "ip_day": ip_day, "device_day": device_day, "device_30d": device_month},
    )
    return entitlement


def entitlement_for_user(user):
    link = TrialAccountLink.objects.select_related("entitlement").filter(user=user).first()
    return link.entitlement if link else None


def trial_usage(entitlement):
    return ExamUsageRecord.objects.filter(
        trial_entitlement=entitlement, status=ExamUsageRecord.Status.COMMITTED,
    ).count()


class TrialQuotaExceeded(ValueError):
    pass


def lock_and_validate_trial(user):
    """Called inside the existing usage transaction before reserving one use."""
    link = TrialAccountLink.objects.filter(user=user).values_list("entitlement_id", flat=True).first()
    if not link:
        return None
    entitlement = TrialEntitlement.objects.select_for_update().get(pk=link)
    if entitlement.status == TrialEntitlement.Status.REVOKED:
        raise TrialQuotaExceeded("Quyền dùng thử đã bị thu hồi.")
    if entitlement.status == TrialEntitlement.Status.REVIEW_REQUIRED and not entitlement.is_verified:
        raise TrialQuotaExceeded("Quyền dùng thử đang chờ quản trị viên xác nhận.")
    if entitlement.expires_at and timezone.now() >= entitlement.expires_at:
        raise TrialQuotaExceeded("Quyền dùng thử đã hết hạn.")
    if trial_usage(entitlement) >= entitlement.quota_total:
        raise TrialQuotaExceeded("Bạn đã sử dụng hết số lượt dùng thử.")
    return entitlement
