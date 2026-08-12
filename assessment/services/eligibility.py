"""Authoritative question eligibility gates.

No NLS or AI classification is inferred from stem text, topic, or keywords.
Only structured data supplied by the bank may open the graduation gate.
"""

GRAD_NLS_ALLOWED = {"PASS", "NOT_APPLICABLE_CONFIRMED"}
AI_DIRECT_TASKS = {"PASS", "PASS_DIRECT", "DIRECT", "DIRECT_ASSESSMENT"}


def graduation_eligible(question) -> bool:
    if question.process_status != "READY_FOR_GRADUATION":
        return False
    if not question.curriculum_id or not question.outcome_id:
        return False
    if question.grad_nls_task not in GRAD_NLS_ALLOWED:
        return False
    if question.graduation_gate != "PASS" or question.import_warnings:
        return False
    metadata = question.source_metadata or {}
    ai_integration = str(metadata.get("AI_INTEGRATION") or "").upper()
    if ai_integration in {"DIRECT", "DIRECT_ASSESSMENT", "YES", "TRUE"}:
        return question.grad_ai_task in AI_DIRECT_TASKS
    return True
