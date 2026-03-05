from django.core.management.base import BaseCommand
from django.db.models import Count
from problems.models import Tag

class Command(BaseCommand):
    help = "Tự động sửa các tag bị trùng slug trong DB (giữ 1 bản)."

    def handle(self, *args, **kwargs):
        self.stdout.write("🔍 Đang quét các slug trùng...")

        dups = (
            Tag.objects.values("slug")
            .annotate(c=Count("id"))
            .filter(c__gt=1)
        )

        if not dups:
            self.stdout.write("✔ Không có slug trùng.")
            return

        for item in dups:
            slug = item["slug"]
            tags = Tag.objects.filter(slug=slug).order_by("id")
            keep = tags.first()

            self.stdout.write(f"⚠ Slug trùng: {slug} → giữ ID {keep.id}")

            for t in tags.exclude(id=keep.id):
                self.stdout.write(f"   → Xóa Tag ID {t.id} ({t.name})")
                # chuyển bài toán sang tag giữ lại
                for p in t.problem_set.all():
                    p.tags.add(keep)
                    p.tags.remove(t)
                t.delete()

        self.stdout.write("🎉 Hoàn tất fix duplicate slug!")
