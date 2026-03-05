from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db import transaction
from problems.models import Tag, Problem
import re


def normalize_slug(s):
    """Chuẩn hóa slug về dạng duy nhất để phát hiện trùng"""
    s = s.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


class Command(BaseCommand):
    help = "Dọn sạch toàn bộ tag trùng slug trong DB (gộp về 1 tag duy nhất)"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 Đang quét tag trùng slug...")

        all_tags = Tag.objects.all()

        # Map slug_norm → list tags có slug này
        bucket = {}

        for tag in all_tags:
            norm = normalize_slug(tag.slug)
            bucket.setdefault(norm, []).append(tag)

        count_trouble = 0

        for norm_slug, tags in bucket.items():
            if len(tags) <= 1:
                continue  # OK

            self.stdout.write(f"\n⚠ Trùng slug chuẩn hóa: {norm_slug}")

            # Giữ lại bản ghi nhỏ nhất ID
            tags = sorted(tags, key=lambda t: t.id)
            keep = tags[0]

            self.stdout.write(f"   → Giữ tag ID {keep.id} ({keep.name})")

            # Bản ghi chính phải có slug đúng chuẩn
            keep.slug = norm_slug
            keep.save()

            for t in tags[1:]:
                self.stdout.write(f"   → Xóa tag ID {t.id} ({t.name})")

                # Chuyển toàn bộ Problem sang tag giữ lại
                for p in Problem.objects.filter(tags=t):
                    p.tags.add(keep)
                    p.tags.remove(t)

                t.delete()

            count_trouble += 1

        if count_trouble == 0:
            self.stdout.write("✔ Không có trùng slug nào.")
        else:
            self.stdout.write(f"\n🎉 Hoàn tất dọn slug! Đã xử lý {count_trouble} nhóm trùng.")

        self.stdout.write("\nBạn có thể chạy:  python manage.py sync_tags")
