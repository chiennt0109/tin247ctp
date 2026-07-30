from dataclasses import dataclass, asdict

from django.db import transaction
from django.utils import timezone

from assessment.models import (
    BankQuestion, ExamAttempt, ExamBlueprint, ExamSession, GeneratedExam,
    GeneratedExamQuestion, ScoringScheme,
)


@dataclass
class Phase4CleanupReport:
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
        candidates = self.candidates()
        return Phase4CleanupReport(
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
