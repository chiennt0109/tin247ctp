# ============================================================
# ?? problems/load_default_tags.py
# Script n?p toàn b? TAG m?c d?nh vào DB
# ============================================================

from problems.models import Tag
from problems.views_admin import TAG_RULES, normalize_tag_name
import re

def load_tags():
    print("?? Loading default tags...")

    count = 0
    for tag in TAG_RULES.keys():
        name = normalize_tag_name(tag)
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

        obj, created = Tag.objects.get_or_create(
            name=name,
            defaults={"slug": slug}
        )
        if created:
            count += 1
            print(f"  ? Added: {name}")

    print(f"? DONE! Total new tags added: {count}")
