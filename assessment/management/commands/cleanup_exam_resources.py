import json
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from assessment.models import ExamResourcePackage, ExamUsageRecord


class Command(BaseCommand):
    help = "Dọn reservation/package tài nguyên đề bị treo hoặc lỗi cũ."

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument("--dry-run", action="store_true")
        mode.add_argument("--apply", action="store_true")
        parser.add_argument("--stale-minutes", type=int, default=60)
        parser.add_argument("--failed-days", type=int, default=7)

    def handle(self, *args, **options):
        now = timezone.now()
        stale_before = now - timedelta(minutes=options["stale_minutes"])
        failed_before = now - timedelta(days=options["failed_days"])
        reserved = ExamUsageRecord.objects.filter(
            status=ExamUsageRecord.Status.RESERVED, created_at__lt=stale_before,
        )
        pending = ExamResourcePackage.objects.filter(
            status=ExamResourcePackage.Status.PENDING, created_at__lt=stale_before,
        )
        failed = ExamResourcePackage.objects.filter(
            status=ExamResourcePackage.Status.FAILED, created_at__lt=failed_before,
        )
        report = {
            "stale_reserved_usage": reserved.count(),
            "stale_pending_packages": pending.count(),
            "old_failed_packages": failed.count(),
            "mode": "DRY_RUN" if options["dry_run"] else "APPLY",
        }
        if options["dry_run"]:
            self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
            return
        with transaction.atomic():
            released = reserved.update(status=ExamUsageRecord.Status.RELEASED)
            pending.update(status=ExamResourcePackage.Status.FAILED)
            deleted_failed, _ = failed.delete()
        report.update({"released_usage": released, "deleted_failed_rows": deleted_failed})
        self.stdout.write(json.dumps(report, ensure_ascii=False, indent=2))
