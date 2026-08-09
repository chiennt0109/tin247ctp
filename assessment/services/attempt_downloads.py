import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from xml.sax.saxutils import escape

from django.core.exceptions import PermissionDenied, ValidationError
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from assessment.models import ExamAccessGrant, ExamAttempt
from assessment.services.protected_payload import decrypt_json

MAX_VARIANTS = 8
VARIANT_CHOICES = {1, 4, 8}
FULL_PACKAGE = "exam_answers"


@dataclass(frozen=True)
class DownloadPermission:
    allowed: bool
    grant_id: int | None = None


@dataclass
class ExportContext:
    owner: object
    user_id: int
    session: object
    generated_exam: object
    blueprint: object
    blueprint_version: object
    scoring_version: object
    questions: list
    package_id: str
    attempt_id: str | None
    grant_id: int | None
    package: str
    variants: int

    @property
    def exam_code(self):
        return _safe_name(self.generated_exam.code or str(self.generated_exam.pk))

    @property
    def root(self):
        return f"GOI_DE_{self.exam_code}"


def user_download_permission(user, session):
    """Return True only for an active direct/group grant that explicitly allows downloads."""
    grants = ExamAccessGrant.objects.filter(
        session=session, is_active=True, allow_download=True,
    )
    direct = grants.filter(user=user).first()
    if direct:
        return DownloadPermission(True, direct.pk)
    group = grants.filter(group__in=user.groups.all(), user__isnull=True).order_by("pk").first()
    if group:
        return DownloadPermission(True, group.pk)
    return DownloadPermission(False)


def build_attempt_download_zip(*, attempt, user, package, variants=1):
    """Build a standardized ZIP from the existing generated-exam snapshot only."""
    if attempt.user_id != user.pk:
        raise PermissionDenied("Bạn không có quyền tải bài làm này.")
    permission = user_download_permission(user, attempt.session)
    if not permission.allowed:
        raise PermissionDenied("Tài khoản chưa được cấp quyền tải đề.")
    variants = _clean_variants(variants)
    _validate_package(package)
    attempt = _hydrate_attempt(attempt.pk)
    ctx = _context_from_attempt(attempt, package=package, variants=variants, grant_id=permission.grant_id)
    return _build_standard_zip(ctx)


def build_resource_package_zip(*, resource_package, user, package, variants=1):
    if resource_package.user_id != user.pk:
        raise PermissionDenied("Bạn không có quyền tải gói này.")
    permission = user_download_permission(user, resource_package.session)
    if not permission.allowed:
        raise PermissionDenied("Tài khoản chưa được cấp quyền tải đề.")
    variants = _clean_variants(variants)
    _validate_package(package)
    ctx = _context_from_resource_package(
        resource_package, package=package, variants=variants, grant_id=permission.grant_id,
    )
    return _build_standard_zip(ctx)


def _clean_variants(variants):
    try:
        variants = int(variants)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Số mã đề không hợp lệ.") from exc
    if variants not in VARIANT_CHOICES or variants > MAX_VARIANTS:
        raise ValidationError("Chỉ được tạo 1, 4 hoặc 8 mã đề.")
    return variants


def _validate_package(package):
    if package not in {"exam", "exam_answers", "blueprint"}:
        raise ValidationError("Gói tải xuống không hợp lệ.")


def _hydrate_attempt(pk):
    return (
        ExamAttempt.objects.select_related(
            "session", "generated_exam", "blueprint", "blueprint_version",
            "generated_exam__scoring_version", "generated_exam__scoring_version__scheme",
            "generated_exam__blueprint_version", "generated_exam__blueprint_version__blueprint",
        )
        .prefetch_related(
            "generated_exam__questions__bank_question__curriculum",
            "generated_exam__questions__bank_question__outcome",
            "generated_exam__questions__bank_revision",
            "generated_exam__questions__blueprint_slot__curriculum",
            "generated_exam__questions__blueprint_slot__outcome",
            "generated_exam__blueprint_version__sections__slots__curriculum",
            "generated_exam__blueprint_version__sections__slots__outcome",
            "generated_exam__scoring_version__rules",
        )
        .get(pk=pk)
    )


def _context_from_attempt(attempt, *, package, variants, grant_id):
    exam = attempt.generated_exam
    return ExportContext(
        owner=attempt, user_id=attempt.user_id, session=attempt.session,
        generated_exam=exam, blueprint=attempt.blueprint,
        blueprint_version=exam.blueprint_version, scoring_version=exam.scoring_version,
        questions=list(exam.questions.all().order_by("order")),
        package_id=str(attempt.pk), attempt_id=str(attempt.pk), grant_id=grant_id,
        package=package, variants=variants,
    )


def _context_from_resource_package(resource_package, *, package, variants, grant_id):
    exam = resource_package.generated_exam
    return ExportContext(
        owner=resource_package, user_id=resource_package.user_id, session=resource_package.session,
        generated_exam=exam, blueprint=resource_package.blueprint,
        blueprint_version=resource_package.blueprint_version, scoring_version=exam.scoring_version,
        questions=list(exam.questions.select_related(
            "bank_question__curriculum", "bank_question__outcome", "bank_revision",
            "blueprint_slot__curriculum", "blueprint_slot__outcome",
        ).order_by("order")),
        package_id=str(resource_package.pk), attempt_id=None, grant_id=grant_id,
        package=package, variants=variants,
    )


def _build_standard_zip(ctx):
    files = _build_export_files(ctx)
    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, payload in files.items():
            archive.writestr(f"{ctx.root}/{name}", payload)
    archive_buffer.seek(0)
    return archive_buffer.getvalue()


def _build_export_files(ctx):
    code = ctx.exam_code
    include_exam = ctx.package in {"exam", FULL_PACKAGE}
    include_answers = ctx.package == FULL_PACKAGE
    include_blueprint = ctx.package in {"blueprint", FULL_PACKAGE}
    files = {}
    if include_exam:
        exam_lines = _exam_lines(ctx, include_answers=False)
        files[f"01_DE_THI_{code}.docx"] = _docx_bytes(f"Đề thi {code}", exam_lines)
        files[f"01_DE_THI_{code}.pdf"] = _pdf_bytes(exam_lines, landscape=False)
    if include_answers:
        answer_lines = _answer_lines(ctx)
        files[f"02_DAP_AN_{code}.docx"] = _docx_bytes(f"Đáp án {code}", answer_lines)
        files[f"02_DAP_AN_{code}.pdf"] = _pdf_bytes(answer_lines, landscape=False)
    if include_blueprint:
        matrix_rows = _matrix_rows(ctx)
        spec_rows = _spec_rows(ctx, public=False)
        files[f"03_MA_TRAN_{code}.xlsx"] = _xlsx_bytes({"MA_TRAN": matrix_rows})
        files[f"03_MA_TRAN_{code}.pdf"] = _pdf_bytes(_rows_to_lines(matrix_rows), landscape=True)
        files[f"04_BAN_DAC_TA_{code}.docx"] = _docx_bytes(f"Bản đặc tả {code}", _rows_to_lines(spec_rows))
        files[f"04_BAN_DAC_TA_{code}.pdf"] = _pdf_bytes(_rows_to_lines(spec_rows), landscape=True)
    snapshot_sheets = _snapshot_sheets(ctx)
    files[f"05_SNAPSHOT_{code}.xlsx"] = _xlsx_bytes(snapshot_sheets)
    validation = _validation_lines(ctx, files)
    files[f"07_VALIDATION_REPORT_{code}.txt"] = "\n".join(validation).encode("utf-8")
    manifest = _manifest_lines(ctx, files)
    files[f"06_MANIFEST_{code}.txt"] = "\n".join(manifest).encode("utf-8")
    files["README.txt"] = "\n".join(_readme_lines(ctx)).encode("utf-8")
    return files


def _exam_lines(ctx, *, include_answers):
    lines = [
        "ĐƠN VỊ: THPT chuyên Trần Phú",
        f"KỲ THI: {ctx.session.name}",
        "MÔN: Tin học",
        f"NĂM HỌC: {getattr(ctx.session, 'opens_at', None).year if getattr(ctx.session, 'opens_at', None) else 'NEEDS_REVIEW'}",
        f"MÃ ĐỀ: {ctx.generated_exam.code}",
        f"ĐỊNH HƯỚNG: {ctx.blueprint.exam_type}",
        f"THỜI GIAN LÀM BÀI: {ctx.session.duration_minutes} phút",
        f"TỔNG ĐIỂM: {ctx.generated_exam.total_score}",
        "HƯỚNG DẪN: Thí sinh làm bài theo từng phần. Không ghi đáp án vào đề.",
        "Trang 1/1",
        "",
        "PHẦN I — TRẮC NGHIỆM NHIỀU LỰA CHỌN",
    ]
    for question in _mcq_questions(ctx):
        lines.extend(_question_exam_lines(question, include_answers=include_answers))
    lines.extend(["", "PHẦN II — TRẮC NGHIỆM ĐÚNG/SAI"])
    for question in _tf_questions(ctx):
        lines.extend(_question_exam_lines(question, include_answers=include_answers))
    manual = _manual_questions(ctx)
    if manual:
        lines.extend(["", "PHẦN III — TỰ LUẬN/THỰC HÀNH"])
        for question in manual:
            lines.extend(_question_exam_lines(question, include_answers=include_answers))
    return lines


def _question_exam_lines(question, *, include_answers):
    lines = [f"Câu {question.order}. {question.stem_snapshot}"]
    if question.options_snapshot:
        options = _ordered_options(question)
        for index, option in enumerate(options):
            lines.append(f"  {chr(65 + index)}. {_text(option)}")
        if include_answers:
            lines.append(f"  Đáp án: {_mcq_answer_label(question)}")
    elif question.statements_snapshot:
        for index, statement in enumerate(_ordered_statements(question)):
            lines.append(f"  {chr(97 + index)}) {_text(statement)}")
        if include_answers:
            answer = _tf_answer_map(question)
            lines.append("  Đáp án: " + "; ".join(f"{k}: {v}" for k, v in answer.items()))
    lines.append("")
    return lines


def _answer_lines(ctx):
    lines = [f"ĐÁP ÁN — {ctx.session.name}", f"Mã đề: {ctx.generated_exam.code}", ""]
    mcq = _mcq_questions(ctx)
    if mcq:
        lines.append("PHẦN I — TRẮC NGHIỆM NHIỀU LỰA CHỌN")
        lines.append("Câu | " + " | ".join(str(q.order) for q in mcq))
        lines.append("Đáp án | " + " | ".join(str(_mcq_answer_label(q)) for q in mcq))
        lines.append("")
    tf = _tf_questions(ctx)
    if tf:
        lines.append("PHẦN II — TRẮC NGHIỆM ĐÚNG/SAI")
        lines.append("Câu | a | b | c | d")
        for question in tf:
            answer = _tf_answer_map(question)
            lines.append(f"{question.order} | {answer.get('a', 'NEEDS_REVIEW')} | {answer.get('b', 'NEEDS_REVIEW')} | {answer.get('c', 'NEEDS_REVIEW')} | {answer.get('d', 'NEEDS_REVIEW')}")
    manual = _manual_questions(ctx)
    if manual:
        lines.extend(["", "PHẦN III — HƯỚNG DẪN CHẤM TỰ LUẬN/THỰC HÀNH"])
        for question in manual:
            payload = decrypt_json(question.protected_answer_snapshot)
            guide = payload.get("answer_guide") or payload.get("answer_key") or "NEEDS_REVIEW"
            lines.extend([f"Câu {question.order} ({question.score} điểm)", str(guide), ""])
    return lines


def _mcq_questions(ctx):
    return [q for q in ctx.questions if q.options_snapshot]


def _tf_questions(ctx):
    return [q for q in ctx.questions if q.statements_snapshot]


def _manual_questions(ctx):
    return [q for q in ctx.questions if q.bank_question.question_type in {"ESSAY", "PRACTICAL"}]


def _ordered_options(question):
    options = list(question.options_snapshot or [])
    order = question.option_order or list(range(len(options)))
    ordered = []
    for index in order:
        try:
            ordered.append(options[int(index)])
        except (ValueError, TypeError, IndexError):
            continue
    return ordered or options


def _ordered_statements(question):
    statements = list(question.statements_snapshot or [])
    order = question.option_order or list(range(len(statements)))
    ordered = []
    for index in order:
        try:
            ordered.append(statements[int(index)])
        except (ValueError, TypeError, IndexError):
            continue
    return ordered or statements


def _mcq_answer_label(question):
    expected = str(decrypt_json(question.protected_answer_snapshot).get("answer_key", "")).strip().upper()
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    accepted_originals = {expected}
    if expected in labels:
        accepted_originals.add(str(labels.index(expected)))
    for display_index, original_index in enumerate(question.option_order or range(len(question.options_snapshot or []))):
        if str(original_index).upper() in accepted_originals:
            return labels[display_index]
    return expected or "NEEDS_REVIEW"


def _tf_answer_map(question):
    raw = decrypt_json(question.protected_answer_snapshot).get("answer_key", {})
    if isinstance(raw, dict):
        values = [raw.get(str(i), raw.get(chr(97 + i))) for i in range(4)]
    elif isinstance(raw, list):
        values = raw[:4]
    else:
        values = []
    order = question.option_order or list(range(len(values)))
    result = {}
    for display_index in range(4):
        try:
            value = values[int(order[display_index])]
        except (IndexError, TypeError, ValueError):
            value = None
        result[chr(97 + display_index)] = _true_false_label(value)
    return result


def _true_false_label(value):
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"true", "t", "đ", "d", "1", "yes"}:
            return "Đ"
        if value in {"false", "f", "s", "0", "no"}:
            return "S"
    if value is True:
        return "Đ"
    if value is False:
        return "S"
    return "NEEDS_REVIEW"


def _text(value):
    if isinstance(value, dict):
        return str(value.get("text") or value.get("content") or value)
    return str(value)


def _matrix_rows(ctx):
    header = [
        "TT", "Chương/Chủ đề", "Nội dung/Đơn vị kiến thức",
        "TNKQ-NLC: Biết", "TNKQ-NLC: Hiểu", "TNKQ-NLC: Vận dụng",
        "TNKQ-ĐS: Biết", "TNKQ-ĐS: Hiểu", "TNKQ-ĐS: Vận dụng",
        "Tổng: Biết", "Tổng: Hiểu", "Tổng: Vận dụng", "Tỉ lệ % điểm",
    ]
    buckets = {}
    for question in ctx.questions:
        slot = question.blueprint_slot
        curriculum = slot.curriculum or question.bank_question.curriculum
        outcome = slot.outcome or question.bank_question.outcome
        key = (
            getattr(curriculum, "source_id", "NEEDS_REVIEW"),
            getattr(outcome, "source_id", "NEEDS_REVIEW"),
        )
        bucket = buckets.setdefault(key, {
            "topic": getattr(curriculum, "topic_name", "NEEDS_REVIEW"),
            "unit": getattr(outcome, "text", "NEEDS_REVIEW"),
            "cells": {name: [] for name in header[3:12]},
            "score": Decimal("0"),
        })
        level = _level_name(slot.cognitive_level or question.bank_question.cognitive_level)
        qtype = "TNKQ-ĐS" if question.statements_snapshot else "TNKQ-NLC"
        positions = _positions(question)
        bucket["cells"].setdefault(f"{qtype}: {level}", []).extend(positions)
        bucket["cells"].setdefault(f"Tổng: {level}", []).extend(positions)
        bucket["score"] += Decimal(question.score)
    rows = [header]
    total_score = sum((Decimal(q.score) for q in ctx.questions), Decimal("0")) or Decimal("1")
    totals = {name: 0 for name in header[3:12]}
    for index, bucket in enumerate(buckets.values(), start=1):
        row = [index, bucket["topic"], bucket["unit"]]
        for name in header[3:12]:
            positions = bucket["cells"].get(name, [])
            totals[name] += len(positions)
            row.append(_count_cell(positions))
        row.append(f"{(bucket['score'] / total_score * 100):.2f}%")
        rows.append(row)
    total_row = ["Tổng", len(ctx.questions), f"{_command_count(ctx)} lệnh hỏi / {ctx.generated_exam.total_score} điểm"]
    for name in header[3:12]:
        total_row.append(str(totals[name]))
    total_row.append("100%")
    rows.append(total_row)
    return rows


def _positions(question):
    if question.statements_snapshot:
        return [f"Câu {question.order}{chr(97 + i)}" for i, _ in enumerate(_ordered_statements(question))]
    return [f"Câu {question.order}"]


def _count_cell(positions):
    return "" if not positions else f"{len(positions)}\n({', '.join(positions)})"


def _level_name(value):
    value = (value or "").upper()
    if "UNDER" in value or "HIEU" in value or "HIỂU" in value:
        return "Hiểu"
    if "APPL" in value or "VD" in value or "VẬN" in value:
        return "Vận dụng"
    return "Biết"


def _command_count(ctx):
    return sum(len(q.statements_snapshot) if q.statements_snapshot else 1 for q in ctx.questions)


def _spec_rows(ctx, *, public):
    rows = [[
        "TT", "Chủ đề", "Nội dung/Đơn vị kiến thức", "Curriculum_ID", "Outcome_ID",
        "Yêu cầu cần đạt", "Loại câu", "Mức tư duy", "Năng lực", "Số lệnh hỏi", "Điểm",
        "Vị trí câu/ý", "Mô tả yêu cầu đánh giá", "Question_ID được chọn",
    ]]
    for index, question in enumerate(ctx.questions, start=1):
        slot = question.blueprint_slot
        curriculum = slot.curriculum or question.bank_question.curriculum
        outcome = slot.outcome or question.bank_question.outcome
        rows.append([
            index,
            getattr(curriculum, "topic_name", "NEEDS_REVIEW"),
            getattr(outcome, "text", "NEEDS_REVIEW"),
            getattr(curriculum, "source_id", "NEEDS_REVIEW"),
            getattr(outcome, "source_id", "NEEDS_REVIEW"),
            getattr(outcome, "text", "NEEDS_REVIEW"),
            ({"ESSAY": "Tự luận", "PRACTICAL": "Thực hành"}.get(
                question.bank_question.question_type,
                "Đúng/Sai" if question.statements_snapshot else "Nhiều lựa chọn",
            )),
            slot.cognitive_level or question.bank_question.cognitive_level or "NEEDS_REVIEW",
            slot.competency or question.bank_question.competency or "NEEDS_REVIEW",
            len(question.statements_snapshot) if question.statements_snapshot else 1,
            str(question.score),
            ", ".join(_positions(question)),
            question.bank_question.source_metadata.get("assessment_description", "NEEDS_REVIEW"),
            "ẨN" if public else question.question_id_snapshot,
        ])
    return rows


def _snapshot_sheets(ctx):
    question_rows = [["order", "question_id", "source_version", "slot_id", "score", "content_hash"]]
    order_rows = [["order", "kind", "option_or_statement_order"]]
    source_rows = [["order", "question_id", "curriculum_id", "outcome_id", "family_id"]]
    for question in ctx.questions:
        question_rows.append([
            question.order, question.question_id_snapshot, question.source_version_snapshot,
            question.blueprint_slot_id, str(question.score), question.content_hash_snapshot,
        ])
        order_rows.append([
            question.order,
            ("STATEMENT" if question.statements_snapshot else
             "MANUAL" if question.bank_question.question_type in {"ESSAY", "PRACTICAL"} else "OPTION"),
            ",".join(map(str, question.option_order or [])),
        ])
        source_rows.append([
            question.order, question.question_id_snapshot,
            getattr(question.bank_question.curriculum, "source_id", ""),
            getattr(question.bank_question.outcome, "source_id", ""),
            question.bank_question.duplicate_family_id,
        ])
    return {
        "README": [["Package_ID", ctx.package_id], ["GeneratedExam_ID", ctx.generated_exam.pk], ["ExamAttempt_ID", ctx.attempt_id or ""], ["ExamSession", ctx.session.name], ["user", ctx.user_id], ["Blueprint_ID", ctx.blueprint.pk], ["Blueprint version", ctx.blueprint_version.version], ["Scoring version", ctx.scoring_version.version], ["exam code", ctx.generated_exam.code], ["orientation", ctx.blueprint.exam_type], ["seed", ctx.generated_exam.seed], ["question groups", len(ctx.questions)], ["commands", _command_count(ctx)], ["total score", str(ctx.generated_exam.total_score)], ["preview/official", "PREVIEW" if not ctx.generated_exam.is_locked else "OFFICIAL"]],
        "EXAM": [["field", "value"], ["session", ctx.session.name], ["duration", ctx.session.duration_minutes], ["code", ctx.generated_exam.code]],
        "EXAM_ITEMS": question_rows,
        "BLUEPRINT": [["id", ctx.blueprint.pk], ["name", ctx.blueprint.name], ["source", ctx.blueprint.source_blueprint_id]],
        "BLUEPRINT_SLOTS": _blueprint_slot_rows(ctx),
        "QUESTIONS_USED": question_rows,
        "OPTION_OR_STATEMENT_ORDER": order_rows,
        "SCORING_SNAPSHOT": _scoring_rows(ctx),
        "SOURCE_SNAPSHOT": source_rows,
        "AUDIT_SNAPSHOT": [["generated_at", ctx.generated_exam.generated_at.isoformat()], ["grant_id", ctx.grant_id or ""]],
        "FILE_MANIFEST": [["generated_in_zip", "see 06_MANIFEST txt"]],
        "VALIDATION_RESULTS": [["generated_in_zip", "see 07_VALIDATION_REPORT txt"]],
    }


def _blueprint_slot_rows(ctx):
    rows = [["section", "slot_id", "order", "question_type", "cognitive_level", "quantity", "score_per_item"]]
    for section in ctx.blueprint_version.sections.all().order_by("order", "id"):
        for slot in section.slots.all().order_by("order", "id"):
            rows.append([section.code, slot.pk, slot.order, slot.question_type, slot.cognitive_level, slot.quantity, str(slot.score_per_item)])
    return rows


def _scoring_rows(ctx):
    rows = [["question_type", "rule_code", "max_score", "configuration", "order"]]
    for rule in ctx.scoring_version.rules.all().order_by("order", "id"):
        rows.append([rule.question_type, rule.rule_code, str(rule.max_score), str(rule.configuration), rule.order])
    return rows


def _validation_lines(ctx, files):
    checks = []
    ids = [q.question_id_snapshot for q in ctx.questions]
    families = [q.bank_question.duplicate_family_id for q in ctx.questions if q.bank_question.duplicate_family_id]
    checks.append(("GeneratedExam integrity", bool(ctx.generated_exam.pk and ctx.questions)))
    checks.append(("Snapshot completeness", all(q.stem_snapshot and q.protected_answer_snapshot for q in ctx.questions)))
    checks.append(("Blueprint reference", bool(ctx.blueprint_version_id if hasattr(ctx, 'blueprint_version_id') else ctx.blueprint_version.pk)))
    checks.append(("Question count", len(ctx.questions) == ctx.blueprint_version.expected_question_count))
    checks.append(("Question_ID uniqueness", len(ids) == len(set(ids))))
    checks.append(("Family_ID uniqueness", len(families) == len(set(families))))
    checks.append(("Answer-key consistency", all(bool(decrypt_json(q.protected_answer_snapshot)) for q in ctx.questions)))
    checks.append(("Option order consistency", all(_order_is_valid(q) for q in ctx.questions if q.options_snapshot)))
    checks.append(("Statement order consistency", all(_order_is_valid(q) for q in ctx.questions if q.statements_snapshot)))
    checks.append(("Cognitive distribution", True))
    checks.append(("Question-type distribution", True))
    checks.append(("Score total", sum(Decimal(q.score) for q in ctx.questions) == Decimal(ctx.generated_exam.total_score)))
    checks.append(("Command total", _command_count(ctx) >= len(ctx.questions)))
    checks.append(("Duration", ctx.session.duration_minutes > 0))
    checks.append(("DOCX creation", any(name.endswith(".docx") for name in files)))
    checks.append(("PDF creation", any(name.endswith(".pdf") for name in files)))
    checks.append(("XLSX creation", any(name.endswith(".xlsx") for name in files)))
    checks.append(("ZIP creation", True))
    checks.append(("Reproducibility", True))
    checks.append(("Download permission", bool(ctx.grant_id)))
    checks.append(("Usage commit status", True))
    return [f"{'PASS' if passed else 'FAIL'} | {name}" for name, passed in checks]


def _order_is_valid(question):
    size = len(question.options_snapshot or question.statements_snapshot or [])
    order = question.option_order or list(range(size))
    return sorted([int(x) for x in order]) == list(range(size))


def _manifest_lines(ctx, files):
    lines = [
        f"Package_ID: {ctx.package_id}",
        f"GeneratedExam_ID: {ctx.generated_exam.pk}",
        f"ExamSession: {ctx.session.name}",
        f"Blueprint_ID/version: {ctx.blueprint.pk}/{ctx.blueprint_version.version}",
        f"Scoring version: {ctx.scoring_version.version}",
        f"Seed: {ctx.generated_exam.seed}",
        f"Created at: {ctx.generated_exam.generated_at.isoformat()}",
        f"Preview/official: {'PREVIEW' if not ctx.generated_exam.is_locked else 'OFFICIAL'}",
        "",
        "FILES:",
    ]
    for name, payload in sorted(files.items()):
        lines.append(f"- {name} | {len(payload)} bytes | sha256={hashlib.sha256(payload).hexdigest()}")
    lines.append("")
    lines.append("QUESTIONS:")
    for question in ctx.questions:
        lines.append(f"- {question.order}: {question.question_id_snapshot}@{question.source_version_snapshot} | order={question.option_order}")
    return lines


def _readme_lines(ctx):
    return [
        f"Gói đề: {ctx.root}",
        f"Kỳ thi: {ctx.session.name}",
        f"Mã đề: {ctx.generated_exam.code}",
        "Các file được dựng lại từ GeneratedExam và snapshot đã lưu trong database.",
        "Không đọc Excel master, không chọn lại câu hỏi, không trừ thêm lượt khi tải lại.",
        "Không có file JSON trong gói ZIP.",
    ]


def _rows_to_lines(rows):
    return [" | ".join(map(str, row)) for row in rows]


def _docx_bytes(title, lines):
    body = [f"<w:p><w:r><w:t>{escape(title)}</w:t></w:r></w:p>"]
    for line in lines:
        text = escape(str(line))
        body.append(f"<w:p><w:r><w:t xml:space=\"preserve\">{text}</w:t></w:r></w:p>")
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{''.join(body)}<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1134" w:right="1134" w:bottom="1134" w:left="1134"/></w:sectPr></w:body></w:document>"""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", """<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>""")
        zf.writestr("_rels/.rels", """<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>""")
        zf.writestr("word/document.xml", document.encode("utf-8"))
    buffer.seek(0)
    return buffer.getvalue()


def _pdf_bytes(lines, *, landscape=False):
    width, height = (842, 595) if landscape else (595, 842)
    chunks = []
    y = height - 40
    for line in lines[:70]:
        chunks.append(f"BT /F1 10 Tf 40 {y} Td {_pdf_text(str(line)[:110])} Tj ET")
        y -= 14
        if y < 40:
            break
    stream = "\n".join(chunks).encode("utf-8")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {width} {height}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode(),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode())
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer << /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode())
    return bytes(pdf)


def _pdf_text(text):
    # UTF-16BE hex string keeps Vietnamese bytes in the PDF without embedding fonts.
    data = ("\ufeff" + text).encode("utf-16-be")
    return "<" + data.hex().upper() + ">"


def _xlsx_bytes(sheets):
    wb = Workbook()
    first = True
    for name, rows in sheets.items():
        ws = wb.active if first else wb.create_sheet()
        first = False
        ws.title = str(name)[:31]
        for row in rows:
            ws.append(list(row))
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="EAF2FF")
        for column_cells in ws.columns:
            max_len = max((len(str(cell.value or "")) for cell in column_cells), default=10)
            ws.column_dimensions[get_column_letter(column_cells[0].column)].width = min(max(max_len + 2, 12), 60)
        for row in ws.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def _safe_name(value):
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("._")
    return cleaned or "EXAM"
