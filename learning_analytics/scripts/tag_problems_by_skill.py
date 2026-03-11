from django.db import transaction

from learning_analytics.models import ProblemSkill, Skill
from problems.models import Problem

TAG_TO_SKILL = {
    "bfs": "BFS",
    "dfs": "DFS",
    "dijkstra": "Dijkstra",
    "dp": "DP Basics",
    "segment-tree": "Segment Tree",
    "segment tree": "Segment Tree",
    "dsu": "Disjoint Set Union",
    "math": "Modular Arithmetic",
    "number-theory": "Prime Factorization",
    "string": "String Matching Basics",
    "flow": "Network Flow",
    "greedy": "Greedy Implementation",
    "binary-search": "Binary Search",
}


def run():
    linked = 0
    with transaction.atomic():
        for problem in Problem.objects.prefetch_related("tags").all():
            tag_keys = set()
            for tag in problem.tags.all():
                tag_keys.add(tag.slug.lower())
                tag_keys.add(tag.name.lower())
            for key in tag_keys:
                if key in TAG_TO_SKILL:
                    skill = Skill.objects.filter(name=TAG_TO_SKILL[key]).first()
                    if skill:
                        _, created = ProblemSkill.objects.get_or_create(problem=problem, skill=skill)
                        linked += int(created)
    return linked
