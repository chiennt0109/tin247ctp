import json
from pathlib import Path

from django.utils.text import slugify

from learning_analytics.models import Skill, SkillPrerequisite


def run(dataset_path=None):
    dataset = Path(dataset_path or "learning_analytics/data/skills.json")
    data = json.loads(dataset.read_text())

    skills_map = {}
    for item in data:
        skill, _ = Skill.objects.update_or_create(
            name=item["name"],
            defaults={
                "slug": slugify(item["name"]),
                "category": item["category"],
                "level": item["level"],
                "description": item.get("description", ""),
            },
        )
        skills_map[item["name"]] = skill

    for item in data:
        skill = skills_map[item["name"]]
        for prereq_name in item.get("prerequisites", []):
            prereq = skills_map.get(prereq_name) or Skill.objects.filter(name=prereq_name).first()
            if prereq:
                SkillPrerequisite.objects.get_or_create(skill=skill, prerequisite=prereq)

    return len(skills_map)
