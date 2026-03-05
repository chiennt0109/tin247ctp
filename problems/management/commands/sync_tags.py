from django.core.management.base import BaseCommand
from problems.models import Tag
from django.utils.text import slugify


TAG_LIST = [
    # Core
    "General",
    "Implementation",
    "Brute Force",

    # Searching
    "Binary Search",
    "Two Pointers",
    "Sliding Window",

    # Array / Prefix
    "Array",
    "Prefix Sum",
    "Difference Array",

    # DP
    "Dynamic Programming",
    "Knapsack",
    "Bitmask",
    "Bitmask DP",
    "Digit DP",
    "DP On Tree",

    # Graph (FULL)
    "Graph",
    "BFS/DFS",
    "Connected Components",
    "Bipartite Graph",
    "Cycle Detection",
    "Tree",
    "Tree Traversal",
    "LCA",
    "Shortest Path",
    "Minimum Spanning Tree",

    # Data Structures
    "Segment Tree",
    "Fenwick Tree",

    # String
    "String",
    "KMP",
    "Manacher",
    "Hash",
    "Hash String",

    # Math
    "Number Theory",
    "Combinatorics",
    "Probability",

    # Special
    "Greedy",
]



def make_slug(name):
    """Slug không dùng viết thường toàn bộ, vì KMP → kmp không đẹp"""
    s = name.lower().replace(" ", "-")
    s = s.replace("’", "")
    return s


class Command(BaseCommand):
    help = "Đồng bộ tag chuẩn cho Semantic Engine v3 (không xóa tag đang dùng)"

    def handle(self, *args, **options):

        self.stdout.write("🔄 Đang đồng bộ tag chuẩn...")

        existing = {t.name: t for t in Tag.objects.all()}
        created = 0
        updated = 0

        for name in TAG_LIST:
            slug = make_slug(name)

            # Nếu tồn tại name → update slug nếu cần
            if name in existing:
                tag = existing[name]
                if tag.slug != slug:
                    tag.slug = slug
                    tag.save()
                    updated += 1
                continue

            # Nếu slug tồn tại nhưng name khác → đổi name
            slug_collision = Tag.objects.filter(slug=slug).first()
            if slug_collision:
                slug_collision.name = name
                slug_collision.save()
                updated += 1
                continue

            # Tạo mới
            Tag.objects.get_or_create(name=name, defaults={"slug": slug})
            created += 1

        self.stdout.write(f"✅ Hoàn tất: tạo mới {created}, cập nhật {updated}")
        self.stdout.write("🎉 Tagset Engine v3 đã sẵn sàng!")
