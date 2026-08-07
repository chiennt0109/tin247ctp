from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist

from assessment.models import ExamUsageRecord
from assessment.services.general_it_trial import lock_and_validate_trial


def committed_usage_count(user, session):
    return ExamUsageRecord.objects.filter(
        user=user, exam_session=session, status=ExamUsageRecord.Status.COMMITTED,
    ).count()


def usage_breakdown(user, session):
    records = ExamUsageRecord.objects.filter(
        user=user, exam_session=session, status=ExamUsageRecord.Status.COMMITTED,
    )
    online = records.filter(usage_type=ExamUsageRecord.UsageType.ONLINE_ATTEMPT).count()
    packages = records.filter(usage_type=ExamUsageRecord.UsageType.DOWNLOAD_PACKAGE).count()
    result = {"online_attempts": online, "download_packages": packages, "total": online + packages}
    try:
        entitlement = user.general_it_trial_link.entitlement
    except (AttributeError, ObjectDoesNotExist):
        return result
    result.update({
        "trial_total": entitlement.quota_total,
        "trial_used": entitlement.quota_used,
        "trial_remaining": entitlement.quota_remaining,
        "trial_status": entitlement.status,
    })
    return result


def reserve_usage(*, user, session, usage_type, idempotency_key):
    existing = ExamUsageRecord.objects.filter(
        user=user, exam_session=session, idempotency_key=idempotency_key,
    ).first()
    if existing:
        return existing, False
    entitlement = lock_and_validate_trial(user)
    record, created = ExamUsageRecord.objects.get_or_create(
        user=user, exam_session=session, idempotency_key=idempotency_key,
        defaults={
            "usage_type": usage_type, "status": ExamUsageRecord.Status.RESERVED,
            "trial_entitlement": entitlement,
        },
    )
    return record, created


def commit_usage(record, *, attempt=None, package=None):
    record.exam_attempt = attempt
    record.resource_package = package
    record.status = ExamUsageRecord.Status.COMMITTED
    record.committed_at = timezone.now()
    record.save(update_fields=(
        "exam_attempt", "resource_package", "status", "committed_at",
    ))
    if record.trial_entitlement_id:
        entitlement = record.trial_entitlement
        now = timezone.now()
        entitlement.first_used_at = entitlement.first_used_at or now
        entitlement.last_used_at = now
        entitlement.save(update_fields=("first_used_at", "last_used_at"))
    return record


def release_usage(record):
    record.status = ExamUsageRecord.Status.RELEASED
    record.save(update_fields=("status",))
    return record
