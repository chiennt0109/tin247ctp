from collections import defaultdict

from learning_analytics.models import Skill


def _bucket(diff):
    diff = (diff or "").lower()
    if diff == "easy":
        return "beginner"
    if diff == "medium":
        return "intermediate"
    return "advanced"


class SkillCoverageAnalyzer:
    def analyze(self):
        rows = []
        missing = []
        weak = []
        missing_beginner = []
        missing_advanced = []

        for skill in Skill.objects.all().prefetch_related("problem_skills__problem"):
            counts = defaultdict(int)
            links = list(skill.problem_skills.all())
            for link in links:
                counts[_bucket(link.problem.difficulty)] += 1
            total = len(links)

            statuses = []
            if total == 0:
                statuses.append("missing")
                missing.append(skill.name)
            if total < 3:
                statuses.append("weak coverage")
                weak.append(skill.name)
            if counts["beginner"] == 0:
                statuses.append("beginner gap")
                missing_beginner.append(skill.name)
            if counts["advanced"] == 0:
                statuses.append("advanced gap")
                missing_advanced.append(skill.name)

            rows.append(
                {
                    "skill": skill.name,
                    "problems": total,
                    "beginner": counts["beginner"],
                    "intermediate": counts["intermediate"],
                    "advanced": counts["advanced"],
                    "status": ", ".join(statuses) if statuses else "ok",
                }
            )

        return {
            "rows": sorted(rows, key=lambda x: (x["status"] != "ok", x["skill"])),
            "missing_skills": sorted(set(missing)),
            "weak_skills": sorted(set(weak)),
            "skills_missing_beginner": sorted(set(missing_beginner)),
            "skills_missing_advanced": sorted(set(missing_advanced)),
        }
