import hashlib
import secrets

from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.utils import timezone

from assessment.models import AssessmentAuditLog, ExamResourcePackage, ExamSession, ExamUsageRecord
from assessment.services.attempt_downloads import build_resource_package_zip, user_download_permission
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.exam_generator import ExamGenerationError, ExamGenerator
from assessment.services.session_configuration import resolve_locked_configuration
from assessment.services.start_attempt import _group_configuration, effective_exam_access
from assessment.services.usage_ledger import commit_usage, committed_usage_count, reserve_usage


class ResourcePackageError(ValueError):
    pass


def _package_identity(session, user, number):
    nonce = secrets.token_hex(16)
    seed = hashlib.sha256(
        f"download:{session.pk}:{user.pk}:{number}:{nonce}".encode()
    ).hexdigest()
    return seed, f"D{user.pk}-P{number}"


def _snapshot_questions(exam):
    return [
        {
            "order": question.order,
            "question_id": question.question_id_snapshot,
            "stem": question.stem_snapshot,
            "options": question.options_snapshot,
            "statements": question.statements_snapshot,
            "score": str(question.score),
        }
        for question in exam.questions.all().order_by("order")
    ]


def _snapshot_answers(exam):
    return {
        str(question.order): question.protected_answer_snapshot
        for question in exam.questions.all().order_by("order")
    }


def _snapshot_scoring(scoring_version):
    return {
        "version_id": scoring_version.pk,
        "total_score": str(scoring_version.total_score),
        "rounding_digits": scoring_version.rounding_digits,
        "rules": [
            {
                "question_type": rule.question_type,
                "rule_code": rule.rule_code,
                "max_score": str(rule.max_score),
                "configuration": rule.configuration,
            }
            for rule in scoring_version.rules.all().order_by("order", "id")
        ],
    }


def create_resource_package(user, exam_session, *, idempotency_key):
    permission = user_download_permission(user, exam_session)
    if not permission.allowed:
        raise ResourcePackageError("Tài khoản chưa được cấp quyền tạo đề tải.")
    try:
        with transaction.atomic():
            session = ExamSession.objects.select_for_update().select_related(
                "blueprint_version", "scoring_version",
            ).get(pk=exam_session.pk)
            now = timezone.now()
            if session.status != ExamSession.Status.OPEN or now < session.opens_at or now >= session.closes_at:
                raise ResourcePackageError("Kỳ kiểm tra chưa mở hoặc đã đóng.")
            access = effective_exam_access(user, session, now=now)
            if not access.allowed:
                raise ResourcePackageError(access.reason)
            if access.max_attempts is not None and committed_usage_count(user, session) >= access.max_attempts:
                raise ResourcePackageError("Bạn đã sử dụng hết số lượt làm.")
            usage, created = reserve_usage(
                user=user, session=session,
                usage_type=ExamUsageRecord.UsageType.DOWNLOAD_PACKAGE,
                idempotency_key=idempotency_key,
            )
            if not created and usage.status == ExamUsageRecord.Status.COMMITTED and usage.resource_package_id:
                return usage.resource_package
            if not created and usage.status == ExamUsageRecord.Status.RESERVED:
                raise ResourcePackageError("Yêu cầu tạo gói đang được xử lý, vui lòng thử lại.")
            package_number = ExamResourcePackage.objects.filter(user=user, session=session).count() + 1
            seed, code = _package_identity(session, user, package_number)
            blueprint_version = session.blueprint_version
            scoring_version = session.scoring_version
            if session.blueprint_group_id:
                blueprint_version, scoring_version = _group_configuration(session, user)
            else:
                blueprint_version, scoring_version = resolve_locked_configuration(blueprint_version.blueprint)
            validation = BlueprintValidator().validate(
                blueprint_version, scoring_version=scoring_version,
            )
            if not validation["valid"]:
                raise ResourcePackageError(
                    f"Không thể sinh đề: {BlueprintValidator.format_failure(validation)}"
                )
            exam = ExamGenerator().generate_for_attempt(
                session, code=code, seed=seed, actor=user,
                blueprint_version=blueprint_version, scoring_version=scoring_version,
            )
            question_snapshot = _snapshot_questions(exam)
            manifest = {
                "download_variants": [1, 4, 8],
                "source": "generated_exam_snapshot",
                "generated_exam_id": exam.pk,
            }
            content_hash = hashlib.sha256(
                repr((question_snapshot, blueprint_version.pk, scoring_version.pk, seed)).encode()
            ).hexdigest()
            package = ExamResourcePackage.objects.create(
                user=user, session=session, generated_exam=exam,
                blueprint=blueprint_version.blueprint, blueprint_version=blueprint_version,
                seed=seed, question_snapshot=question_snapshot,
                answer_snapshot=_snapshot_answers(exam),
                scoring_snapshot=_snapshot_scoring(scoring_version),
                manifest=manifest, content_hash=content_hash,
                status=ExamResourcePackage.Status.READY,
            )
            commit_usage(usage, package=package)
            AssessmentAuditLog.objects.create(
                action="CREATE_RESOURCE_PACKAGE", actor=user, object_type="ExamResourcePackage",
                object_id=str(package.pk), details={"usage_record_id": usage.pk},
            )
            return package
    except ExamGenerationError as exc:
        raise ResourcePackageError(str(exc)) from exc
    except IntegrityError as exc:
        raise ResourcePackageError("Không thể tạo gói tài nguyên do xung đột dữ liệu.") from exc


def download_package_zip(package, user, *, package_type, variants=1):
    if package.user_id != user.pk:
        raise PermissionDenied("Bạn không có quyền tải gói này.")
    payload = build_resource_package_zip(
        resource_package=package, user=user, package=package_type, variants=variants,
    )
    package.last_downloaded_at = timezone.now()
    package.save(update_fields=("last_downloaded_at",))
    return payload
