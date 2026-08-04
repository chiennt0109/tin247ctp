from collections import Counter, defaultdict
from decimal import Decimal
from statistics import median

from django.contrib.auth import get_user_model

from assessment.models import ExamAttempt, GradingResult


def official_attempts(attempts, policy):
    grouped = defaultdict(list)
    for attempt in attempts:
        grouped[attempt.user_id].append(attempt)
    selected = set()
    for rows in grouped.values():
        rows.sort(key=lambda item: item.attempt_number)
        if policy == "FIRST":
            chosen = rows[0]
        elif policy == "LAST":
            chosen = rows[-1]
        elif policy == "HIGHEST":
            chosen = max(rows, key=lambda item: (item.score or Decimal("-1"), -item.attempt_number))
        elif policy == "AVERAGE":
            selected.update(item.pk for item in rows)
            chosen = None
        else:
            chosen = rows[-1]
        if chosen:
            selected.add(chosen.pk)
    return selected


def _breakdown(details, key):
    values = defaultdict(lambda: {"score": Decimal("0"), "max_score": Decimal("0"), "questions": 0})
    for item in details:
        bucket = values[item.get(key) or "Chưa phân loại"]
        bucket["score"] += Decimal(item["score"])
        bucket["max_score"] += Decimal(item["max_score"])
        bucket["questions"] += 1
    return [{"name": name, **value} for name, value in sorted(values.items())]


def student_result_summary(attempt):
    result = attempt.grading_results.get(is_current=True)
    return {
        "result": result,
        "sections": _breakdown(result.detail, "section"),
        "topics": _breakdown(result.detail, "topic"),
        "outcomes": _breakdown(result.detail, "learning_outcome"),
        "cognitive_levels": _breakdown(result.detail, "cognitive_level"),
    }


def exam_results_dashboard(session):
    attempts = list(session.attempts.select_related("user").all())
    graded = [item for item in attempts if item.status == ExamAttempt.Status.GRADED]
    results = list(GradingResult.objects.filter(attempt__in=graded, is_current=True).select_related("attempt"))
    scores = [float(result.total_score) for result in results]
    status_counts = Counter(item.status for item in attempts)
    if session.access_mode == session.AccessMode.ALL_USERS:
        eligible = get_user_model().objects.filter(is_active=True).count()
    elif session.access_mode == session.AccessMode.SELECTED_GROUPS:
        eligible = get_user_model().objects.filter(groups__in=session.access_groups.all(), is_active=True).distinct().count()
    else:
        eligible = None
    question_stats = defaultdict(lambda: {
        "uses": 0, "answers": 0, "correct": 0, "blank": 0, "options": Counter(), "responses": [],
    })
    for result in results:
        for item in result.detail:
            stats = question_stats[item["question_id"]]
            stats["uses"] += 1
            stats["responses"].append((float(result.total_score), item["outcome"] == "CORRECT"))
            if item["outcome"] == "BLANK":
                stats["blank"] += 1
            else:
                stats["answers"] += 1
                stats["correct"] += item["outcome"] == "CORRECT"
                stats["options"][str(item.get("selected_option") or item.get("submitted_answer"))] += 1
    questions = []
    overall_median = median(scores) if scores else 0
    for question_id, stats in sorted(question_stats.items()):
        uses = stats["uses"]
        correct_rate = stats["correct"] / uses if uses else 0
        blank_rate = stats["blank"] / uses if uses else 0
        discrimination = 0.0
        if len(stats["responses"]) >= 4:
            ordered = sorted(stats["responses"])
            half = max(len(ordered) // 2, 1)
            discrimination = (
                sum(correct for _score, correct in ordered[-half:]) / half
                - sum(correct for _score, correct in ordered[:half]) / half
            )
        warnings = []
        if uses >= 5 and correct_rate >= .9:
            warnings.append("Câu quá dễ")
        if uses >= 5 and correct_rate <= .2:
            warnings.append("Câu quá khó hoặc có dấu hiệu sai đáp án")
        if uses >= 5 and blank_rate >= .5:
            warnings.append("Tỉ lệ bỏ trống bất thường")
        questions.append({
            "question_id": question_id,
            **{key: value for key, value in stats.items() if key != "responses"},
            "correct_rate": correct_rate,
            "blank_rate": blank_rate, "difficulty_observed": 1 - correct_rate,
            "discrimination_index": discrimination, "warnings": warnings,
        })
    histogram = Counter(int(score) for score in scores)
    all_details = [item for result in results for item in result.detail]
    return {
        "eligible": eligible, "attempts": len(attempts), "status_counts": status_counts,
        "not_started": max((eligible or 0) - len({item.user_id for item in attempts}), 0),
        "average": sum(scores) / len(scores) if scores else None,
        "median": overall_median if scores else None, "highest": max(scores) if scores else None,
        "lowest": min(scores) if scores else None, "histogram": sorted(histogram.items()),
        "questions": questions,
        "topics": _breakdown(all_details, "topic"),
        "outcomes": _breakdown(all_details, "learning_outcome"),
        "cognitive_levels": _breakdown(all_details, "cognitive_level"),
    }
