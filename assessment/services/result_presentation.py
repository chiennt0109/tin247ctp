from assessment.services.grading import truth_values
from assessment.services.protected_payload import decrypt_json


PARTS = (
    ("MCQ_SINGLE", "Phần I — Trắc nghiệm nhiều phương án"),
    ("TRUE_FALSE_GROUP", "Phần II — Trắc nghiệm Đúng/Sai"),
)


def result_sections(attempt, result):
    """Return result rows in the same part/order layout as the attempt page."""
    details = {
        str(item.get("exam_question_id")): item
        for item in result.detail
    }
    questions = list(
        attempt.generated_exam.questions.select_related("bank_question")
        .only(
            "order", "statements_snapshot", "protected_answer_snapshot",
            "bank_question__question_type",
        )
        .order_by("order")
    )
    grouped = {question_type: [] for question_type, _title in PARTS}
    grouped["OTHER"] = []
    for question in questions:
        question_type = question.bank_question.question_type
        key = question_type if question_type in grouped else "OTHER"
        detail = dict(details.get(str(question.pk), {}))
        detail.update({"question": question, "question_type": question_type})
        if question_type == "TRUE_FALSE_GROUP":
            detail["statements"] = _true_false_statements(question, detail)
        grouped[key].append(detail)

    sections = []
    for question_type, title in (*PARTS, ("OTHER", "Phần khác")):
        rows = grouped[question_type]
        if not rows:
            continue
        for part_order, row in enumerate(rows, start=1):
            row["part_order"] = part_order
        sections.append({"question_type": question_type, "title": title, "rows": rows})
    return sections


def _true_false_statements(question, detail):
    expected = decrypt_json(question.protected_answer_snapshot)
    expected_values = truth_values(
        expected.get("answer_key"), len(question.statements_snapshot),
    )
    if detail.get("outcome") == "BLANK":
        submitted_values = [None] * len(question.statements_snapshot)
    else:
        submitted_values = truth_values(
            detail.get("submitted_answer"), len(question.statements_snapshot),
        )
    rows = []
    for index, statement in enumerate(question.statements_snapshot):
        correct_value = expected_values[index] if index < len(expected_values) else False
        submitted_value = submitted_values[index] if index < len(submitted_values) else False
        rows.append({
            "label": statement.get("label") if isinstance(statement, dict) else None,
            "text": statement.get("text", statement) if isinstance(statement, dict) else statement,
            "correct_value": correct_value,
            "submitted_value": submitted_value,
            "is_correct": submitted_value is not None and submitted_value == correct_value,
        })
    return rows
