from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from assessment.models import (
    AssessmentAuditLog, BankQuestion, BlueprintSection, BlueprintSlot, BlueprintVersion,
    ExamBlueprint, ExamParticipant, ExamSession, GeneratedExam, GeneratedExamAsset,
    GeneratedExamQuestion, ScoringRule, ScoringScheme, ScoringSchemeVersion,
)
from assessment.services.bank_importer import WorkbookBankImporter
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.exam_session import publish_exam_session


LEGACY_TYPES = {
    "TN_4_LUA_CHON": "MCQ_SINGLE", "DUNG_SAI": "TRUE_FALSE_GROUP",
    "TRA_LOI_NGAN": "SHORT_ANSWER", "MCQ": "MCQ_SINGLE",
}


@dataclass
class DemoSeedReport:
    dry_run: bool
    bank: dict = field(default_factory=dict)
    blueprints_created: int = 0
    blueprints_existing: int = 0
    schemes_created: int = 0
    schemes_existing: int = 0
    sessions_created: int = 0
    sessions_existing: int = 0
    generated: list = field(default_factory=list)
    participants: list = field(default_factory=list)
    slot_reports: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    reset_counts: dict = field(default_factory=dict)


class AssessmentDemoSeeder:
    BLUEPRINTS = (
        ("practice", "[DEMO] Luyện tập tổng hợp", 12, "PRACTICE"),
        ("periodic", "[DEMO] Kiểm tra định kỳ", 24, "PERIODIC"),
        ("graduation", "[DEMO] Thi thử tốt nghiệp", 28, "GRADUATION"),
    )

    def __init__(self, workbook_path):
        self.workbook_path = Path(workbook_path)
        self.parsed = WorkbookBankImporter().parse(self.workbook_path)
        self.warnings = []
        if self.parsed.errors:
            self.warnings.append(
                f"Master parser reported {len(self.parsed.errors)} validation errors; demo uses only synchronized valid BankQuestion rows."
            )

    def plan(self):
        report = DemoSeedReport(dry_run=True, bank=self._bank_counts(), warnings=list(self.warnings))
        for key, name, target, purpose in self.BLUEPRINTS:
            specs = self._graduation_specs(target) if key == "graduation" else self._derived_specs(purpose, target)
            for spec in specs:
                available = self._spec_queryset(spec).count()
                report.slot_reports.append({
                    "blueprint": name, "required": spec["quantity"], "candidates": available,
                    "status": "SUFFICIENT" if available > spec["quantity"] * 2 else "TIGHT",
                    "topic": spec["curriculum_id"], "outcome": spec["outcome_id"],
                    "level": spec["level"], "question_type": spec["question_type"],
                })
            if sum(spec["quantity"] for spec in specs) < (10 if key == "practice" else target):
                report.warnings.append(f"{name}: current eligible pool cannot reach the demo target; session will remain DRAFT.")
        report.blueprints_created = sum(
            not ExamBlueprint.objects.filter(demo_key=f"assessment-demo-{key}").exists()
            for key, _name, _target, _purpose in self.BLUEPRINTS
        )
        report.blueprints_existing = len(self.BLUEPRINTS) - report.blueprints_created
        report.schemes_created = sum(
            not ScoringScheme.objects.filter(demo_key=f"assessment-demo-{key}").exists()
            for key, _name, _target, _purpose in self.BLUEPRINTS
        )
        report.schemes_existing = len(self.BLUEPRINTS) - report.schemes_created
        session_slugs = self._session_definitions().keys()
        report.sessions_created = sum(
            not ExamSession.objects.filter(demo_key=slug).exists()
            and not ExamSession.objects.filter(slug=slug, is_demo=True).exists()
            for slug in session_slugs
        )
        report.sessions_existing = len(self._session_definitions()) - report.sessions_created
        return report

    @transaction.atomic
    def apply(self, *, student=None, teacher=None):
        report = DemoSeedReport(dry_run=False, bank=self._bank_counts(), warnings=list(self.warnings))
        artifacts = {}
        for key, name, target, purpose in self.BLUEPRINTS:
            blueprint, scheme, validation = self._ensure_blueprint_and_scheme(
                key, name, target, purpose, teacher=teacher,
            )
            artifacts[key] = (blueprint, scheme, validation)
            if getattr(blueprint, "_demo_created", False):
                report.blueprints_created += 1
            else:
                report.blueprints_existing += 1
            if getattr(scheme, "_demo_created", False):
                report.schemes_created += 1
            else:
                report.schemes_existing += 1
            report.slot_reports.extend(self._slot_report(name, validation))

        sessions = {}
        for slug, definition in self._session_definitions().items():
            artifact_key = definition.pop("artifact")
            blueprint, scheme, validation = artifacts[artifact_key]
            session = ExamSession.objects.filter(demo_key=slug).first()
            created = False
            if session is None:
                # Adopt demo rows created before ExamSession gained demo_key. The
                # is_demo guard prevents a real session with the same slug from
                # ever being claimed by the seeder.
                session = ExamSession.objects.filter(slug=slug, is_demo=True).first()
                if session is not None:
                    session.demo_key = slug
                    session.save(update_fields=("demo_key",))
            if session is None:
                session = ExamSession.objects.create(
                    slug=slug, demo_key=slug,
                    **definition, blueprint_version=blueprint.versions.get(version=1),
                    scoring_version=scheme.versions.get(version=1), created_by=teacher,
                    is_demo=True,
                )
                created = True
            sessions[slug] = (session, validation)
            report.sessions_created += int(created)
            report.sessions_existing += int(not created)

        if student is None:
            report.warnings.append("No --student supplied; no real student account was guessed or assigned.")
        else:
            for slug, (session, _validation) in sessions.items():
                participant, _ = ExamParticipant.objects.update_or_create(
                    session=session, user=student,
                    defaults=self._participant_defaults(slug),
                )
                report.participants.append(f"{student.username} -> {session.name}")

        for slug, (session, validation) in sessions.items():
            if session.status != ExamSession.Status.DRAFT or session.generated_exams.exists():
                report.generated.extend(self._exam_report(session.generated_exams.all()))
                continue
            if not validation["valid"]:
                report.warnings.append(f"{session.name} remains DRAFT because its blueprint is not valid.")
                continue
            try:
                session, exams = publish_exam_session(session, actor=teacher, base_seed=f"demo:{slug}")
            except ValueError as exc:
                report.warnings.append(f"{session.name} remains DRAFT: {exc}")
                continue
            report.generated.extend(self._exam_report(exams))

        AssessmentAuditLog.objects.create(
            action="SEED_ASSESSMENT_DEMO", actor=teacher, object_type="AssessmentDemo",
            object_id="assessment-demo-v1", details={
                "blueprints_created": report.blueprints_created,
                "sessions_created": report.sessions_created,
            },
        )
        return report

    @transaction.atomic
    def reset(self):
        sessions = ExamSession.objects.filter(is_demo=True)
        exams = GeneratedExam.objects.filter(session__in=sessions)
        exam_questions = GeneratedExamQuestion.objects.filter(exam__in=exams)
        blueprints = ExamBlueprint.objects.filter(is_demo=True)
        schemes = ScoringScheme.objects.filter(is_demo=True)
        counts = {
            "generated_exam_assets": GeneratedExamAsset.objects.filter(exam_question__in=exam_questions).count(),
            "generated_exam_questions": exam_questions.count(), "generated_exams": exams.count(),
            "participants": ExamParticipant.objects.filter(session__in=sessions).count(),
            "sessions": sessions.count(), "blueprints": blueprints.count(), "scoring_schemes": schemes.count(),
        }
        GeneratedExamAsset.objects.filter(exam_question__in=exam_questions).delete()
        exam_questions.delete()
        exams.delete()
        ExamParticipant.objects.filter(session__in=sessions).delete()
        sessions.delete()
        blueprint_versions = BlueprintVersion.objects.filter(blueprint__in=blueprints)
        BlueprintSlot.objects.filter(section__version__in=blueprint_versions).delete()
        BlueprintSection.objects.filter(version__in=blueprint_versions).delete()
        blueprint_versions.delete()
        scoring_versions = ScoringSchemeVersion.objects.filter(scheme__in=schemes)
        ScoringRule.objects.filter(version__in=scoring_versions).delete()
        scoring_versions.delete()
        blueprints.delete()
        schemes.delete()
        return counts

    def _bank_counts(self):
        available = BankQuestion.objects.filter(is_available=True)
        return {
            "available": available.count(),
            "periodic": available.filter(process_status="READY_FOR_PERIODIC").count(),
            "graduation": available.filter(process_status="READY_FOR_GRADUATION").count(),
        }

    def _ensure_blueprint_and_scheme(self, key, name, target, purpose, *, teacher):
        blueprint, created = ExamBlueprint.objects.get_or_create(
            demo_key=f"assessment-demo-{key}",
            defaults={
                "name": name, "exam_type": purpose, "grade": 12, "subject": "Tin học",
                "notes": "Derived from synchronized master projection for assessment testing.",
                "created_by": teacher, "is_demo": True,
            },
        )
        blueprint._demo_created = created
        specs = self._graduation_specs(target) if key == "graduation" else self._derived_specs(purpose, target)
        eligible_count = sum(spec["quantity"] for spec in specs)
        if not specs:
            self.warnings.append(f"{name}: no eligible synchronized questions; blueprint is intentionally partial.")
            specs = self._derived_specs("PRACTICE", min(target, 1), fallback_only=True)
            # The fallback is only structural and remains ineligible for periodic/graduation publish.
        total_score = sum((spec["score"] * spec["quantity"] for spec in specs), Decimal("0"))
        version, version_created = BlueprintVersion.objects.get_or_create(
            blueprint=blueprint, version=1,
            defaults={
                "duration_minutes": 30 if key == "practice" else 50,
                "expected_question_count": sum(spec["quantity"] for spec in specs),
                "expected_total_score": total_score, "created_by": teacher,
                "source_blueprint_id": self._source_blueprint_id() if key == "graduation" else "",
                "source_snapshot": {"workbook": self.workbook_path.name, "demo_key": key},
            },
        )
        if version_created:
            self._create_sections_and_slots(version, specs)

        scheme_name = name.replace("Luyện tập tổng hợp", "Chấm luyện tập").replace(
            "Kiểm tra định kỳ", "Chấm kiểm tra định kỳ"
        ).replace("Thi thử tốt nghiệp", "Chấm thi thử tốt nghiệp")
        scheme, scheme_created = ScoringScheme.objects.get_or_create(
            demo_key=f"assessment-demo-{key}",
            defaults={"name": scheme_name, "created_by": teacher, "is_demo": True},
        )
        scheme._demo_created = scheme_created
        scoring_version, scoring_created = ScoringSchemeVersion.objects.get_or_create(
            scheme=scheme, version=1,
            defaults={
                "total_score": total_score, "rounding_digits": 2, "created_by": teacher,
                "source_snapshot": {"score_rules": self._master_score_rules()},
            },
        )
        if scoring_created:
            self._create_scoring_rules(scoring_version, specs)
        validation = BlueprintValidator().validate(version, scoring_version=scoring_version)
        minimum_required = 10 if key == "practice" else target
        if eligible_count < minimum_required:
            validation["valid"] = False
            validation["errors"].append({
                "code": "DEMO_TARGET_NOT_REACHED", "target": minimum_required,
                "eligible": eligible_count,
            })
            validation["error_counts"]["DEMO_TARGET_NOT_REACHED"] = 1
        if key == "graduation" and eligible_count < target:
            self.warnings.append("DEMO blueprint is partial because the current graduation-ready pool is insufficient.")
        return blueprint, scheme, validation

    def _derived_specs(self, purpose, target, fallback_only=False):
        queryset = BankQuestion.objects.filter(is_available=True, current_revision__isnull=False)
        if not fallback_only:
            queryset = queryset.filter(process_status=f"READY_FOR_{purpose}")
        rows = queryset.values(
            "curriculum_id", "outcome_id", "question_type", "cognitive_level", "difficulty",
            "duplicate_family_id",
        ).order_by("curriculum_id", "outcome_id", "question_type", "cognitive_level", "difficulty")
        groups = defaultdict(list)
        for row in rows:
            key = tuple(row[field] for field in (
                "curriculum_id", "outcome_id", "question_type", "cognitive_level", "difficulty",
            ))
            groups[key].append(row["duplicate_family_id"])
        ranked = []
        for group_key, families in groups.items():
            capacity = len({family or f"EMPTY:{index}" for index, family in enumerate(families)})
            ranked.append((capacity, group_key))
        ranked.sort(key=lambda item: (-item[0], tuple(str(value) for value in item[1])))
        specs, remaining = [], target
        for capacity, group_key in ranked:
            if remaining <= 0:
                break
            quantity = min(capacity, 3, remaining)
            if quantity <= 0:
                continue
            curriculum_id, outcome_id, question_type, level, difficulty = group_key
            specs.append({
                "curriculum_id": curriculum_id, "outcome_id": outcome_id,
                "question_type": question_type, "level": level, "difficulty": difficulty,
                "quantity": quantity, "score": self._score_for_type(question_type),
                "graduation": purpose == "GRADUATION",
                "process_status": "" if fallback_only else f"READY_FOR_{purpose}",
            })
            remaining -= quantity
        return specs

    def _graduation_specs(self, target):
        blueprint_id = self._source_blueprint_id()
        cells = [
            row for row in self.parsed.rows.get("BLUEPRINT_CELLS", [])
            if str(row.get("BLUEPRINT_ID")) == blueprint_id and str(row.get("STATUS")) == "APPROVED"
        ]
        specs, remaining = [], target
        for row in cells:
            if remaining <= 0:
                break
            question_type = LEGACY_TYPES.get(str(row.get("QUESTION_TYPE")), str(row.get("QUESTION_TYPE")))
            queryset = BankQuestion.objects.filter(
                is_available=True, current_revision__isnull=False,
                process_status="READY_FOR_GRADUATION", question_type=question_type,
                curriculum__source_id=str(row.get("CURRICULUM_ID")),
                outcome__source_id=str(row.get("OUTCOME_ID")),
            )
            if row.get("COGNITIVE_LEVEL"):
                queryset = queryset.filter(cognitive_level=str(row.get("COGNITIVE_LEVEL")))
            families = list(queryset.values_list("duplicate_family_id", flat=True))
            capacity = len({family or f"EMPTY:{index}" for index, family in enumerate(families)})
            required = int(row.get("REQUIRED_COUNT") or 0)
            quantity = min(required, capacity, remaining)
            if quantity:
                specs.append({
                    "curriculum_id": queryset.values_list("curriculum_id", flat=True).first(),
                    "outcome_id": queryset.values_list("outcome_id", flat=True).first(),
                    "question_type": question_type, "level": str(row.get("COGNITIVE_LEVEL") or ""),
                    "difficulty": int(row["DIFFICULTY"]) if row.get("DIFFICULTY") else None,
                    "quantity": quantity,
                    "score": Decimal(str(row.get("SCORE_PER_ITEM") or self._score_for_type(question_type))),
                    "graduation": True,
                    "process_status": "READY_FOR_GRADUATION",
                })
                remaining -= quantity
        return specs

    def _source_blueprint_id(self):
        approved = [row for row in self.parsed.rows.get("BLUEPRINTS", []) if str(row.get("STATUS")) == "APPROVED"]
        return str(approved[0].get("BLUEPRINT_ID")) if approved else ""

    def _create_sections_and_slots(self, version, specs):
        by_type = defaultdict(list)
        for spec in specs:
            by_type[spec["question_type"]].append(spec)
        order = 0
        for section_order, (question_type, section_specs) in enumerate(sorted(by_type.items()), 1):
            section = BlueprintSection.objects.create(
                version=version, code=f"S{section_order}", name=question_type, order=section_order,
            )
            for spec in section_specs:
                order += 1
                BlueprintSlot.objects.create(
                    section=section, order=order, curriculum_id=spec["curriculum_id"],
                    outcome_id=spec["outcome_id"], question_type=spec["question_type"],
                    cognitive_level=spec["level"], difficulty=spec["difficulty"],
                    quantity=spec["quantity"], score_per_item=spec["score"],
                    requires_graduation_eligibility=spec["graduation"],
                    required_process_status=spec.get("process_status", ""),
                )

    @staticmethod
    def _spec_queryset(spec):
        queryset = BankQuestion.objects.filter(
            is_available=True, current_revision__isnull=False,
            question_type=spec["question_type"], cognitive_level=spec["level"],
        )
        if spec["curriculum_id"]:
            queryset = queryset.filter(curriculum_id=spec["curriculum_id"])
        if spec["outcome_id"]:
            queryset = queryset.filter(outcome_id=spec["outcome_id"])
        if spec["difficulty"] is not None:
            queryset = queryset.filter(difficulty=spec["difficulty"])
        if spec["graduation"]:
            queryset = queryset.filter(process_status="READY_FOR_GRADUATION")
        elif spec.get("process_status"):
            queryset = queryset.filter(process_status=spec["process_status"])
        return queryset

    def _master_score_rules(self):
        return [
            {key: value for key, value in row.items() if not key.startswith("__")}
            for row in self.parsed.rows.get("SCORE_RULES", [])
            if str(row.get("STATUS")) == "APPROVED"
        ]

    def _score_for_type(self, question_type):
        for row in self._master_score_rules():
            canonical_type = LEGACY_TYPES.get(str(row.get("QUESTION_TYPE")), str(row.get("QUESTION_TYPE")))
            if canonical_type == question_type and row.get("MAX_SCORE") is not None:
                return Decimal(str(row["MAX_SCORE"]))
        self.warnings.append(f"No approved master score rule for {question_type}; using demo-only weight 0.25.")
        return Decimal("0.25")

    def _create_scoring_rules(self, version, specs):
        types = sorted({spec["question_type"] for spec in specs})
        master_rules = self._master_score_rules()
        for order, question_type in enumerate(types, 1):
            source = next((
                row for row in master_rules
                if LEGACY_TYPES.get(str(row.get("QUESTION_TYPE")), str(row.get("QUESTION_TYPE"))) == question_type
            ), None)
            max_score = self._score_for_type(question_type)
            ScoringRule.objects.create(
                version=version, question_type=question_type,
                rule_code=str(source.get("RULE_CODE")) if source else f"DEMO_{question_type}",
                max_score=max_score, order=order,
                configuration={
                    "source": "SCORE_RULES" if source else "DEMO_DERIVED_FROM_BANK_TYPE",
                    "description": str(source.get("RULE_DESCRIPTION")) if source else "No master rule available",
                    "max_score": str(max_score),
                },
            )

    def _session_definitions(self):
        now = timezone.now()
        common = {
            "opens_at": now - timedelta(minutes=5), "closes_at": now + timedelta(days=30),
            "duration_minutes": 30, "shuffle_questions": True, "shuffle_options": True,
            "status": ExamSession.Status.DRAFT,
        }
        return {
            "assessment-demo-practice": {
                **common, "artifact": "practice", "name": "[DEMO] Luyện tập tự do",
                "exam_type": ExamSession.ExamType.PRACTICE, "max_attempts": 3,
                "attempt_result_mode": ExamSession.AttemptResultMode.HIGHEST,
                "generation_mode": ExamSession.GenerationMode.COMMON, "code_count": 1,
                "score_release_mode": ExamSession.ReleaseMode.AFTER_SUBMIT,
                "answer_release_mode": ExamSession.ReleaseMode.AFTER_SUBMIT,
                "release_solutions": True, "allow_review": True,
            },
            "assessment-demo-periodic": {
                **common, "artifact": "periodic", "name": "[DEMO] Kiểm tra định kỳ",
                "exam_type": ExamSession.ExamType.PERIODIC, "max_attempts": 1,
                "generation_mode": ExamSession.GenerationMode.MULTIPLE, "code_count": 4,
                "score_release_mode": ExamSession.ReleaseMode.AFTER_CLOSE,
                "answer_release_mode": ExamSession.ReleaseMode.NEVER,
            },
            "assessment-demo-graduation": {
                **common, "artifact": "graduation", "name": "[DEMO] Thi thử tốt nghiệp",
                "exam_type": ExamSession.ExamType.GRADUATION, "max_attempts": 1,
                "duration_minutes": 50, "generation_mode": ExamSession.GenerationMode.MULTIPLE,
                "code_count": 4, "score_release_mode": ExamSession.ReleaseMode.MANUAL,
                "answer_release_mode": ExamSession.ReleaseMode.NEVER,
            },
            "assessment-demo-access": {
                **common, "artifact": "practice", "name": "[DEMO] Kiểm tra quyền truy cập",
                "exam_type": ExamSession.ExamType.CUSTOM, "max_attempts": 2,
                "generation_mode": ExamSession.GenerationMode.COMMON, "code_count": 1,
                "score_release_mode": ExamSession.ReleaseMode.MANUAL,
                "answer_release_mode": ExamSession.ReleaseMode.MANUAL,
                "allow_exam_download": True, "allow_blueprint_download": True,
            },
        }

    @staticmethod
    def _participant_defaults(slug):
        defaults = {
            "is_enabled": True, "can_access": True, "make_up_allowed": False,
            "allow_after_deadline": False, "can_view_answers": False,
            "can_view_solutions": False, "can_download_exam": False,
            "can_download_blueprint": False,
        }
        if slug == "assessment-demo-practice":
            defaults.update(max_attempts_override=3, can_view_answers=True, can_view_solutions=True)
        elif slug == "assessment-demo-periodic":
            defaults.update(max_attempts_override=1)
        elif slug == "assessment-demo-access":
            defaults.update(can_download_exam=True, can_download_blueprint=True)
        return defaults

    @staticmethod
    def _slot_report(name, validation):
        result = []
        slots = {
            slot.pk: slot for slot in BlueprintSlot.objects.filter(
                pk__in=[item["slot_id"] for item in validation["availability"]]
            ).select_related("curriculum", "outcome")
        }
        for item in validation["availability"]:
            slot = slots[item["slot_id"]]
            result.append({
                "blueprint": name, **item,
                "topic": slot.curriculum.topic_name if slot.curriculum_id else "-",
                "outcome": slot.outcome.text if slot.outcome_id else "-",
                "level": slot.cognitive_level or "-", "question_type": slot.question_type,
            })
        return result

    @staticmethod
    def _exam_report(exams):
        return [{
            "session": exam.session.name, "code": exam.code,
            "questions": exam.questions.count(), "score": str(exam.total_score),
            "blueprint_valid": bool(exam.validation_report.get("valid")),
            "hash": exam.exam_hash,
        } for exam in exams]


def resolve_user(username):
    if not username:
        return None
    try:
        return get_user_model().objects.get(username=username)
    except get_user_model().DoesNotExist as exc:
        raise ValueError(f"User {username!r} does not exist") from exc
