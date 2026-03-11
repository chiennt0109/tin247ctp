from learning_analytics.models import ProblemSkill, Skill

KEYWORD_SKILL_MAP = {
    "bfs": "BFS",
    "breadth first search": "BFS",
    "dfs": "DFS",
    "dijkstra": "Dijkstra",
    "shortest path": "Dijkstra",
    "knapsack": "Knapsack",
    "lis": "LIS",
    "segment tree": "Segment Tree",
    "fenwick": "Fenwick Tree",
    "dsu": "Disjoint Set Union",
    "union find": "Disjoint Set Union",
    "kmp": "KMP",
    "suffix": "Suffix Array",
    "flow": "Network Flow",
}


def detect_skills(problem):
    text = f"{problem.title} {problem.statement}".lower()
    tag_words = []
    for tag in problem.tags.all():
        tag_words.extend([tag.name.lower(), tag.slug.lower()])
    haystack = text + " " + " ".join(tag_words)

    detected = []
    for keyword, skill_name in KEYWORD_SKILL_MAP.items():
        if keyword in haystack:
            skill = Skill.objects.filter(name=skill_name).first()
            if skill and skill not in detected:
                detected.append(skill)
    return detected


def detect_and_assign(problem):
    detected = detect_skills(problem)
    created = 0
    for skill in detected:
        _, was_created = ProblemSkill.objects.get_or_create(problem=problem, skill=skill)
        created += int(was_created)
    return detected, created
