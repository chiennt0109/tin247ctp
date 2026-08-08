import hashlib
import hmac
import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from assessment.models import (
    ExamAccessGrant, ExamSession, TrialAccountLink, TrialAuditEvent, TrialDevice,
    TrialEntitlement,
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


def grant_initial_trial(user, *, actor=None, entitlement=None):
    """Write trial access through the existing per-user × per-session grants."""
    quota = _limit("GENERAL_IT_TRIAL_QUOTA", 3)
    grants = []
    now = timezone.now()
    sessions = ExamSession.objects.filter(
        Q(allow_signup_trial=True)
        | Q(
            status=ExamSession.Status.OPEN,
            opens_at__lte=now,
            closes_at__gt=now,
        )
    ).distinct()
    for session in sessions:
        grant, created = ExamAccessGrant.objects.get_or_create(
            session=session, user=user,
            defaults={
                "limit_mode": ExamAccessGrant.LimitMode.ATTEMPTS,
                "max_attempts": quota,
                "is_active": True,
                "grant_source": ExamAccessGrant.GrantSource.AUTO_TRIAL,
            },
        )
        if created:
            grants.append(grant)
            TrialAuditEvent.objects.create(
                entitlement=entitlement, user=user, actor=actor,
                event_type="TRIAL_ACCESS_GRANT_CREATED",
                details={"session_id": str(session.pk), "max_attempts": quota, "grant_id": grant.pk},
            )
    return grants


@transaction.atomic
def ensure_signup_trial_grants(user):
    """Repair eligible signup grants when an exam opens after registration."""
    if not getattr(settings, "GENERAL_IT_TRIAL_ENABLED", True):
        return []
    link = TrialAccountLink.objects.select_for_update().select_related("entitlement").filter(
        user=user,
    ).first()
    if not link or link.entitlement.status != TrialEntitlement.Status.ACTIVE:
        return []
    eligible_owner = TrialAuditEvent.objects.filter(
        entitlement=link.entitlement, user=user, event_type="SIGNUP_GRANTED",
    ).exists()
    if not eligible_owner:
        return []
    return grant_initial_trial(user, entitlement=link.entitlement)


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
        status=(TrialEntitlement.Status.REVIEW_REQUIRED if review else TrialEntitlement.Status.ACTIVE),
    )
    owns_new_identity = True
    try:
        with transaction.atomic():
            TrialDevice.objects.create(entitlement=entitlement, device_hash=device_hash)
    except IntegrityError:
        # Two simultaneous signups carrying the same cookie converge on the
        # database-unique device row instead of creating two allowances.
        shared = TrialDevice.objects.select_related("entitlement").get(device_hash=device_hash)
        entitlement.delete()
        entitlement = shared.entitlement
        owns_new_identity = False
    TrialAccountLink.objects.create(user=user, entitlement=entitlement)
    if not owns_new_identity:
        TrialAuditEvent.objects.create(
            entitlement=entitlement, user=user,
            event_type="ACCOUNT_LINKED_EXISTING_DEVICE",
            device_hash=device_hash, ip_hash=ip_hash,
            details={"concurrent_signup": True},
        )
        return entitlement
    TrialAuditEvent.objects.create(
        entitlement=entitlement, user=user,
        event_type="SIGNUP_REVIEW_REQUIRED" if review else "SIGNUP_GRANTED",
        device_hash=device_hash, ip_hash=ip_hash,
        details={"ip_hour": ip_hour, "ip_day": ip_day, "device_day": device_day, "device_30d": device_month},
    )
    if not review and owns_new_identity:
        grant_initial_trial(user, entitlement=entitlement)
    return entitlement


def entitlement_for_user(user):
    link = TrialAccountLink.objects.select_related("entitlement").filter(user=user).first()
    return link.entitlement if link else None
