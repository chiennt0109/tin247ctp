import io
import json
import random
import zipfile
from dataclasses import dataclass

from django.core.exceptions import PermissionDenied, ValidationError

from assessment.models import ExamAccessGrant, ExamAttempt
from assessment.services.protected_payload import decrypt_json

MAX_VARIANTS = 8
VARIANT_CHOICES = {1, 4, 8}


@dataclass(frozen=True)
class DownloadPermission:
    allowed: bool
    grant_id: int | None = None


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
    """Build a small, bounded ZIP package from the already-generated attempt snapshot."""
    if attempt.user_id != user.pk:
        raise PermissionDenied("Bạn không có quyền tải bài làm này.")
    permission = user_download_permission(user, attempt.session)
    if not permission.allowed:
        raise PermissionDenied("Tài khoản chưa được cấp quyền tải đề.")
    try:
        variants = int(variants)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Số mã đề không hợp lệ.") from exc
    if variants not in VARIANT_CHOICES or variants > MAX_VARIANTS:
        raise ValidationError("Chỉ được tạo 1, 4 hoặc 8 mã đề.")
    if package not in {"exam", "exam_answers", "blueprint"}:
        raise ValidationError("Gói tải xuống không hợp lệ.")

    attempt = _hydrate_attempt(attempt.pk)
    return _build_zip(attempt=attempt, package=package, variants=variants, grant_id=permission.grant_id)


def build_resource_package_zip(*, resource_package, user, package, variants=1):
    if resource_package.user_id != user.pk:
        raise PermissionDenied("Bạn không có quyền tải gói này.")
    permission = user_download_permission(user, resource_package.session)
    if not permission.allowed:
        raise PermissionDenied("Tài khoản chưa được cấp quyền tải đề.")
    try:
        variants = int(variants)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Số mã đề không hợp lệ.") from exc
    if variants not in VARIANT_CHOICES or variants > MAX_VARIANTS:
        raise ValidationError("Chỉ được tạo 1, 4 hoặc 8 mã đề.")
    if package not in {"exam", "exam_answers", "blueprint"}:
        raise ValidationError("Gói tải xuống không hợp lệ.")
    return _build_zip(
        attempt=_ResourcePackageAttempt(resource_package),
        package=package, variants=variants, grant_id=permission.grant_id,
    )


def _build_zip(*, attempt, package, variants, grant_id):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr("README.txt", _readme(attempt, package, variants, grant_id))
        if package in {"exam", "exam_answers"}:
            include_answers = package == "exam_answers"
            for index in range(1, variants + 1):
                archive.writestr(
                    f"de-thi/ma-{index:02d}.txt",
                    _render_exam_variant(attempt, variant=index, include_answers=include_answers),
                )
        if package in {"exam_answers", "blueprint"}:
            archive.writestr("ma-tran/blueprint.json", _blueprint_payload(attempt))
            archive.writestr("dac-ta/scoring.json", _scoring_payload(attempt))
    buffer.seek(0)
    return buffer.getvalue()


def _hydrate_attempt(pk):
    return (
        ExamAttempt.objects.select_related(
            "session", "generated_exam", "blueprint", "blueprint_version",
            "generated_exam__scoring_version", "generated_exam__scoring_version__scheme",
            "generated_exam__blueprint_version",
        )
        .prefetch_related(
            "generated_exam__questions__bank_question",
            "generated_exam__blueprint_version__sections__slots",
            "generated_exam__scoring_version__rules",
        )
        .get(pk=pk)
    )


def _readme(attempt, package, variants, grant_id):
    return "\n".join([
        f"Kỳ thi: {attempt.session.name}",
        f"Bài làm: {attempt.pk}",
        f"Mã đề gốc: {attempt.generated_exam.code}",
        f"Gói: {package}",
        f"Số mã sinh ra: {variants}",
        f"Grant cho phép tải: {grant_id}",
        "Dữ liệu được tạo từ snapshot đề đã sinh, không truy vấn lại ngân hàng để đổi nội dung.",
    ])


def _render_exam_variant(attempt, *, variant, include_answers):
    rng = random.Random(f"{attempt.generated_exam.seed}:download:{variant}")
    lines = [
        f"{attempt.session.name}",
        f"Mã tải xuống: {variant:02d}",
        f"Thời lượng: {attempt.session.duration_minutes} phút",
        "",
    ]
    for order, question in enumerate(attempt.generated_exam.questions.all().order_by("order"), start=1):
        lines.append(f"Câu {order}. {question.stem_snapshot}")
        if question.options_snapshot:
            options = list(enumerate(question.options_snapshot))
            rng.shuffle(options)
            for display_index, (_original_index, option) in enumerate(options):
                label = chr(ord("A") + display_index)
                text = option.get("text", option) if isinstance(option, dict) else option
                lines.append(f"  {label}. {text}")
            if include_answers:
                answer = _mcq_answer_label(question, options)
                lines.append(f"  Đáp án: {answer}")
        elif question.statements_snapshot:
            for statement_index, statement in enumerate(question.statements_snapshot, start=1):
                text = statement.get("text", statement) if isinstance(statement, dict) else statement
                lines.append(f"  {statement_index}. {text} [Đúng/Sai]")
            if include_answers:
                answer = decrypt_json(question.protected_answer_snapshot).get("answer_key")
                lines.append(f"  Đáp án: {answer}")
        if include_answers:
            lines.append(f"  Điểm: {question.score}")
        lines.append("")
    return "\n".join(lines)


def _mcq_answer_label(question, shuffled_options):
    expected = decrypt_json(question.protected_answer_snapshot).get("answer_key")
    expected_text = str(expected).strip().upper()
    labels = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    accepted_originals = {expected_text}
    if expected_text in labels:
        accepted_originals.add(str(labels.index(expected_text)))
    for display_index, (_original_display_index, _option) in enumerate(shuffled_options):
        try:
            original_index = question.option_order[_original_display_index]
        except (TypeError, IndexError):
            original_index = _original_display_index
        if str(original_index).upper() in accepted_originals:
            return labels[display_index]
    return expected


def _blueprint_payload(attempt):
    version = attempt.generated_exam.blueprint_version
    payload = {
        "blueprint": {
            "id": attempt.blueprint_id,
            "name": attempt.blueprint.name,
            "source_blueprint_id": attempt.blueprint.source_blueprint_id,
            "exam_type": attempt.blueprint.exam_type,
        },
        "version": {
            "id": version.pk,
            "version": version.version,
            "duration_minutes": version.duration_minutes,
            "expected_question_count": version.expected_question_count,
            "expected_total_score": str(version.expected_total_score),
            "validation_report": version.validation_report,
        },
        "sections": [],
    }
    for section in version.sections.all().order_by("order", "id"):
        payload["sections"].append({
            "code": section.code,
            "name": section.name,
            "order": section.order,
            "instructions": section.instructions,
            "slots": [
                {
                    "order": slot.order,
                    "question_type": slot.question_type,
                    "cognitive_level": slot.cognitive_level,
                    "difficulty": slot.difficulty,
                    "quantity": slot.quantity,
                    "score_per_item": str(slot.score_per_item),
                    "required_tags": slot.required_tags,
                    "excluded_tags": slot.excluded_tags,
                }
                for slot in section.slots.all().order_by("order", "id")
            ],
        })
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _scoring_payload(attempt):
    version = attempt.generated_exam.scoring_version
    payload = {
        "scheme": version.scheme.name,
        "version": version.version,
        "total_score": str(version.total_score),
        "rounding_digits": version.rounding_digits,
        "rules": [
            {
                "question_type": rule.question_type,
                "rule_code": rule.rule_code,
                "max_score": str(rule.max_score),
                "configuration": rule.configuration,
                "order": rule.order,
            }
            for rule in version.rules.all().order_by("order", "id")
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


class _ResourcePackageAttempt:
    def __init__(self, resource_package):
        self.pk = resource_package.pk
        self.user_id = resource_package.user_id
        self.session = resource_package.session
        self.generated_exam = resource_package.generated_exam
        self.blueprint = resource_package.blueprint
        self.blueprint_id = resource_package.blueprint_id
        self.blueprint_version = resource_package.blueprint_version
