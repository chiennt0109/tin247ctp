from dataclasses import dataclass, asdict

from django.db import connection, transaction
from django.utils import timezone

from assessment.models import (
    BankQuestion, ExamAttempt, ExamBlueprint, ExamSession, GeneratedExam,
    GeneratedExamQuestion, ScoringScheme,
)


@dataclass
class Phase4CleanupReport:
    schema_state: str
    legacy_generated_exams: int
    legacy_generated_exam_questions: int
    legacy_exam_assignments: int
    legacy_demo_participants: int
    legacy_preview_exams: int
    orphan_generated_exams: int
    orphan_generated_exam_questions: int
    broken_attempts: int
    obsolete_demo_sessions: int
    preserved: dict

    def as_dict(self):
        return asdict(self)


class Phase4LegacyCleanup:
    ATTEMPT_TABLE = ExamAttempt._meta.db_table
    EXAM_TABLE = GeneratedExam._meta.db_table
    EXAM_QUESTION_TABLE = GeneratedExamQuestion._meta.db_table

    @staticmethod
    def schema_is_current():
        """Return False without querying ORM relations introduced by migration 0007."""
        tables = set(connection.introspection.table_names())
        if Phase4LegacyCleanup.ATTEMPT_TABLE not in tables:
            return False
        with connection.cursor() as cursor:
            columns = {
                column.name
                for column in connection.introspection.get_table_description(
                    cursor, Phase4LegacyCleanup.EXAM_TABLE
                )
            }
        return {"purpose", "expires_at"}.issubset(columns)

    @staticmethod
    def _table_count(table):
        tables = set(connection.introspection.table_names())
        if table not in tables:
            return 0
        quoted = connection.ops.quote_name(table)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) FROM {quoted}")
            return cursor.fetchone()[0]

    @staticmethod
    def candidates():
        expired_previews = GeneratedExam.objects.filter(
            purpose=GeneratedExam.Purpose.PREVIEW,
            expires_at__lte=timezone.now(),
        )
        orphan_attempt_exams = GeneratedExam.objects.filter(
            purpose=GeneratedExam.Purpose.ATTEMPT,
            attempt__isnull=True,
        )
        return (expired_previews | orphan_attempt_exams).distinct()

    def inspect(self):
        if not self.schema_is_current():
            # Pre-0007 production has neither assessment_examattempt nor the
            # GeneratedExam purpose columns. Every existing exam necessarily
            # belongs to the old pre-generation architecture. Use table-level
            # counts only: referencing attempt__isnull would join a table that
            # does not exist and make the safety dry-run unusable.
            legacy_exams = self._table_count(self.EXAM_TABLE)
            return Phase4CleanupReport(
                schema_state="PRE_0007_READ_ONLY",
                legacy_generated_exams=legacy_exams,
                legacy_generated_exam_questions=self._table_count(self.EXAM_QUESTION_TABLE),
                legacy_exam_assignments=0,
                legacy_demo_participants=0,
                legacy_preview_exams=0,
                orphan_generated_exams=0,
                orphan_generated_exam_questions=0,
                broken_attempts=0,
                obsolete_demo_sessions=0,
                preserved={
                    "bank_questions": self._table_count(BankQuestion._meta.db_table),
                    "blueprints": self._table_count(ExamBlueprint._meta.db_table),
                    "scoring_schemes": self._table_count(ScoringScheme._meta.db_table),
                },
            )
        candidates = self.candidates()
        return Phase4CleanupReport(
            schema_state="CURRENT",
            legacy_generated_exams=candidates.count(),
            legacy_generated_exam_questions=GeneratedExamQuestion.objects.filter(exam__in=candidates).count(),
            legacy_exam_assignments=0,
            legacy_demo_participants=0,
            legacy_preview_exams=candidates.filter(purpose=GeneratedExam.Purpose.PREVIEW).count(),
            orphan_generated_exams=GeneratedExam.objects.filter(
                purpose=GeneratedExam.Purpose.ATTEMPT, attempt__isnull=True
            ).count(),
            orphan_generated_exam_questions=0,  # Enforced by a non-null CASCADE foreign key.
            broken_attempts=ExamAttempt.objects.filter(
                status=ExamAttempt.Status.IN_PROGRESS, generated_exam__isnull=True
            ).count(),
            obsolete_demo_sessions=ExamSession.objects.filter(
                is_demo=True, generated_exams__in=candidates
            ).distinct().count(),
            preserved={
                "bank_questions": BankQuestion.objects.count(),
                "blueprints": ExamBlueprint.objects.count(),
                "scoring_schemes": ScoringScheme.objects.count(),
            },
        )

    @transaction.atomic
    def apply(self):
        if not self.schema_is_current():
            raise Phase4CleanupSchemaError(
                "Migration assessment.0007_on_demand_attempts is required before --apply. "
                "Run migrate --plan, migrate, then repeat --dry-run first."
            )
        before = self.inspect()
        broken = ExamAttempt.objects.filter(
            status=ExamAttempt.Status.IN_PROGRESS, generated_exam__isnull=True
        )
        broken.update(
            status=ExamAttempt.Status.INVALIDATED,
            invalidation_reason="Invalidated by Phase 4 legacy cleanup: missing generated exam",
        )
        self.candidates().delete()
        return before, self.inspect()


class Phase4CleanupSchemaError(RuntimeError):
    pass
