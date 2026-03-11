def serialize_user_skill(item):
    return {
        "skill": item.skill.name,
        "score": round(item.skill_score, 4),
        "level": item.level,
        "weakness_score": round(item.weakness_score, 4),
        "last_updated": item.last_updated.isoformat() if item.last_updated else None,
    }


def serialize_problem_recommendation(rec):
    p = rec["problem"]
    return {
        "problem_id": p.id,
        "code": p.code,
        "title": p.title,
        "difficulty": p.difficulty,
        "skill": rec["skill"],
        "score": rec["score"],
    }


def serialize_learning_path(skill, order):
    return {"order": order, "skill": skill.name}
