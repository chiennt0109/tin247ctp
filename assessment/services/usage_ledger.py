from django.utils import timezone

from assessment.models import ExamUsageRecord


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
    return {"online_attempts": online, "download_packages": packages, "total": online + packages}


def reserve_usage(*, user, session, usage_type, idempotency_key):
    existing = ExamUsageRecord.objects.filter(
        user=user, exam_session=session, idempotency_key=idempotency_key,
    ).first()
    if existing:
        return existing, False
    record, created = ExamUsageRecord.objects.get_or_create(
        user=user, exam_session=session, idempotency_key=idempotency_key,
        defaults={"usage_type": usage_type, "status": ExamUsageRecord.Status.RESERVED},
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
    return record


def release_usage(record):
    record.status = ExamUsageRecord.Status.RELEASED
    record.save(update_fields=("status",))
    return record
