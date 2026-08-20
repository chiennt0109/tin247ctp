"""Snapshot helpers for immutable generated-exam payloads."""


def command_count(exam) -> int:
    return sum(4 if q.bank_question.question_type == "TRUE_FALSE_GROUP" else 1
               for q in exam.questions.select_related("bank_question"))

