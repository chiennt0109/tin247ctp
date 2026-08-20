from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from assessment.models import ExamAttempt, GeneratedExam, GradingResult
from assessment.services.protected_payload import decrypt_json


class GradingError(ValueError):
    pass


def _value(payload):
    return payload.get("value") if isinstance(payload, dict) else payload


def _blank(value):
    return value is None or value == "" or value == [] or value == {}


def _decimal(value, *, comma=True):
    if isinstance(value, str) and comma:
        value = value.strip().replace(",", ".")
    return Decimal(str(value))


def _single_choice(question, submitted, expected):
    try:
        displayed_index = int(submitted)
        original_index = question.option_order[displayed_index]
    except (TypeError, ValueError, IndexError):
        return False
    expected_value = expected.get("answer_key")
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    accepted = {str(original_index)}
    if original_index < len(labels):
        accepted.add(labels[original_index])
    option = question.options_snapshot[displayed_index]
    if isinstance(option, dict) and option.get("label"):
        accepted.add(str(option["label"]).strip().upper())
    return str(expected_value).strip().upper() in accepted


def truth_values(value, size):
    if isinstance(value, dict):
        return [bool(value.get(str(index), value.get(index, False))) for index in range(size)]
    if isinstance(value, str):
        parts = [part.strip().upper() for part in value.replace(";", ",").split(",")]
        return [part in {"1", "T", "TRUE", "Đ", "D", "ĐÚNG"} for part in parts]
    if isinstance(value, list):
        if all(isinstance(item, bool) for item in value):
            return value
        selected = {int(item) for item in value if str(item).isdigit()}
        return [index in selected for index in range(size)]
    return []


def _short_answer(submitted, expected, config):
    accepted = expected.get("equivalent_answers") or config.get("equivalent_answers") or []
    answer_key = expected.get("answer_key")
    if answer_key is not None:
        accepted = [answer_key, *accepted]
    normalized = str(submitted).strip().casefold()
    if any(normalized == str(item).strip().casefold() for item in accepted):
        return True
    tolerance = config.get("numeric_tolerance", expected.get("numeric_tolerance"))
    if tolerance is None:
        return False
    try:
        actual = _decimal(submitted, comma=config.get("accept_decimal_comma", True))
        target = _decimal(answer_key, comma=True)
        return abs(actual - target) <= _decimal(tolerance)
    except (InvalidOperation, TypeError, ValueError):
        return False


def _grade_question(question, answer, rule):
    submitted = _value(answer.answer) if answer else None
    maximum = question.score
    if _blank(submitted):
        return Decimal("0"), "BLANK", submitted
    expected = decrypt_json(question.protected_answer_snapshot)
    config = rule.configuration
    if question.bank_question.question_type == "MCQ_SINGLE":
        correct = _single_choice(question, submitted, expected)
        score = _decimal(config.get("correct", maximum)) if correct else _decimal(config.get("incorrect", 0))
    elif question.bank_question.question_type == "TRUE_FALSE_GROUP":
        expected_values = truth_values(expected.get("answer_key"), len(question.statements_snapshot))
        submitted_values = truth_values(submitted, len(question.statements_snapshot))
        correct_items = sum(a == b for a, b in zip(submitted_values, expected_values, strict=False))
        table = config.get("score_by_correct_count", {})
        score = _decimal(table.get(str(correct_items), maximum if correct_items == len(expected_values) else 0))
        correct = bool(expected_values) and correct_items == len(expected_values)
    elif question.bank_question.question_type == "SHORT_ANSWER":
        correct = _short_answer(submitted, expected, config)
        score = maximum if correct else _decimal(config.get("incorrect", 0))
    else:
        raise GradingError(f"Chưa có bộ chấm tự động cho loại {question.bank_question.question_type}.")
    score = min(max(score, Decimal("0")), maximum)
    return score, "CORRECT" if correct else "INCORRECT", submitted


@transaction.atomic
def grade_attempt(attempt_id, *, actor=None, reason="Nộp bài", allow_regrade=False):
    # Lock only the attempt row. ``generated_exam`` is nullable at schema level;
    # joining it in a FOR UPDATE query is rejected by PostgreSQL.
    attempt = ExamAttempt.objects.select_for_update().get(pk=attempt_id)
    if attempt.status not in {
        ExamAttempt.Status.SUBMITTED, ExamAttempt.Status.AUTO_SUBMITTED, ExamAttempt.Status.GRADED,
    }:
        raise GradingError("Chỉ chấm bài đã nộp.")
    current = attempt.grading_results.filter(is_current=True).first()
    if current and not allow_regrade:
        return current

    if not attempt.generated_exam_id:
        raise GradingError("Bài làm không có snapshot đề để chấm.")
    exam = GeneratedExam.objects.select_related("scoring_version").get(
        pk=attempt.generated_exam_id,
    )
    rules = {rule.question_type: rule for rule in exam.scoring_version.rules.all()}
    answers = {answer.exam_question_id: answer for answer in attempt.answers.all()}
    details, total = [], Decimal("0")
    manual_score_required = False
    counts = {"CORRECT": 0, "INCORRECT": 0, "BLANK": 0}
    questions = exam.questions.select_related(
        "bank_question__curriculum", "bank_question__outcome", "blueprint_slot__section",
    ).order_by("order")
    for question in questions:
        if question.bank_question.question_type in {"ESSAY", "PRACTICAL"}:
            manual_score_required = True
            submitted = _value(answers.get(question.pk).answer) if answers.get(question.pk) else None
            details.append({
                "exam_question_id": question.pk, "order": question.order,
                "question_id": question.question_id_snapshot,
                "submitted_answer": submitted, "outcome": "PENDING_MANUAL",
                "score": None, "max_score": str(question.score),
                "manual_score_required": True,
                "answer_guide": decrypt_json(question.protected_answer_snapshot).get("answer_guide")
                    or decrypt_json(question.protected_answer_snapshot).get("answer_key"),
            })
            continue
        rule = rules.get(question.bank_question.question_type)
        if not rule:
            raise GradingError(f"Thiếu quy tắc chấm cho {question.bank_question.question_type}.")
        score, outcome, submitted = _grade_question(question, answers.get(question.pk), rule)
        total += score
        counts[outcome] += 1
        selected_option = None
        if question.bank_question.question_type == "MCQ_SINGLE" and str(submitted).isdigit():
            index = int(submitted)
            if index < len(question.options_snapshot):
                option = question.options_snapshot[index]
                selected_option = option.get("label") if isinstance(option, dict) else str(index)
        details.append({
            "exam_question_id": question.pk, "order": question.order,
            "question_id": question.question_id_snapshot,
            "section": question.blueprint_slot.section.name,
            "topic": (
                question.bank_question.curriculum.topic_name
                if question.bank_question.curriculum_id else "Chưa phân loại"
            ),
            "learning_outcome": (
                question.bank_question.outcome.code
                if question.bank_question.outcome_id else "Chưa phân loại"
            ),
            "cognitive_level": question.bank_question.cognitive_level or "Chưa phân loại",
            "submitted_answer": submitted, "outcome": outcome, "score": str(score),
            "selected_option": selected_option,
            "max_score": str(question.score), "rule_code": rule.rule_code,
        })

    digits = exam.scoring_version.rounding_digits
    quantum = Decimal("1").scaleb(-digits)
    total = total.quantize(quantum, rounding=ROUND_HALF_UP)
    if current:
        current.is_current = False
        current.save(update_fields=("is_current",))
    sequence = (attempt.grading_results.aggregate(value=Max("sequence"))["value"] or 0) + 1
    result = GradingResult.objects.create(
        attempt=attempt, sequence=sequence, scoring_version=exam.scoring_version,
        total_score=total, max_score=exam.total_score, correct_count=counts["CORRECT"],
        incorrect_count=counts["INCORRECT"], blank_count=counts["BLANK"], detail=details,
        graded_by=actor, reason=reason,
    )
    # An auto-grader must never finalize a mixed/manual paper.  The MCQ subtotal
    # remains auditable in GradingResult while the attempt awaits a teacher.
    if not manual_score_required:
        attempt.score = total
        attempt.graded_at = timezone.now()
        attempt.status = ExamAttempt.Status.GRADED
        attempt.save(update_fields=("score", "graded_at", "status"))
    return result
