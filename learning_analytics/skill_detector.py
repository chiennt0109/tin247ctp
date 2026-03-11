import re
import unicodedata

from learning_analytics.models import ProblemSkill, Skill

KEYWORD_SKILL_MAP = {
    "bfs": "BFS",
    "breadth first search": "BFS",
    "dfs": "DFS",
    "depth first search": "DFS",
    "dijkstra": "Dijkstra",
    "shortest path": "Dijkstra",
    "knapsack": "Knapsack",
    "lis": "LIS",
    "longest increasing subsequence": "LIS",
    "segment tree": "Segment Tree",
    "fenwick": "Fenwick Tree",
    "binary indexed tree": "Fenwick Tree",
    "dsu": "Disjoint Set Union",
    "union find": "Disjoint Set Union",
    "kmp": "KMP",
    "suffix array": "Suffix Array",
    "suffix": "Suffix Array",
    "network flow": "Network Flow",
    "max flow": "Network Flow",
    "min cost max flow": "Min Cost Max Flow",
    "topological sort": "Topological Sort",
    "mst": "Minimum Spanning Tree",
    "minimum spanning tree": "Minimum Spanning Tree",
    "lca": "LCA",
    "digit dp": "Digit DP",
    "bitmask dp": "Bitmask DP",
    "tree dp": "Tree DP",
    "scc": "Strongly Connected Components",
    "string matching": "String Matching Basics",
}


def normalize_text(text):
    text = (text or "").lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s\-]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _boundary_match(haystack, phrase):
    phrase = re.escape(phrase)
    return bool(re.search(rf"(?<![a-z0-9]){phrase}(?![a-z0-9])", haystack))


def _skill_alias_map():
    aliases = dict(KEYWORD_SKILL_MAP)
    # include canonical skill names/slugs from DB for broader matching
    for skill in Skill.objects.all():
        aliases[normalize_text(skill.name)] = skill.name
        slug_alias = normalize_text(skill.slug.replace("-", " "))
        aliases[slug_alias] = skill.name
    return aliases


def detect_skill_scores(problem):
    title = normalize_text(getattr(problem, "title", ""))
    statement = normalize_text(getattr(problem, "statement", ""))
    tags = []
    for tag in problem.tags.all():
        tags.extend([normalize_text(tag.name), normalize_text(tag.slug)])
    tags_text = " ".join(tags)

    alias_map = _skill_alias_map()
    scores = {}
    for keyword, skill_name in alias_map.items():
        if not keyword:
            continue
        score = 0
        if _boundary_match(title, keyword):
            score += 3
        if _boundary_match(tags_text, keyword):
            score += 2
        if _boundary_match(statement, keyword):
            score += 1
        if score:
            scores[skill_name] = max(scores.get(skill_name, 0), score)
    return scores


def detect_skills(problem, min_score=2):
    scores = detect_skill_scores(problem)
    skill_names = [name for name, score in scores.items() if score >= min_score]
    skill_qs = Skill.objects.filter(name__in=skill_names)
    skill_map = {s.name: s for s in skill_qs}
    return [skill_map[name] for name in skill_names if name in skill_map]


def detect_and_assign(problem, min_score=2, refresh=False):
    detected = detect_skills(problem, min_score=min_score)
    if refresh:
        ProblemSkill.objects.filter(problem=problem).delete()
    created = 0
    for skill in detected:
        _, was_created = ProblemSkill.objects.get_or_create(problem=problem, skill=skill)
        created += int(was_created)
    return detected, created
