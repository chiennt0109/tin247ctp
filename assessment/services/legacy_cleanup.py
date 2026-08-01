from dataclasses import asdict, dataclass

from django.db import transaction

from assessment.models import ExamAttempt, GeneratedExam, GeneratedExamQuestion


@dataclass
class LegacyCleanupReport:
    legacy_assignments: int
    legacy_generated_exams: int
    orphan_generated_exams: int
    orphan_generated_exam_questions: int
    broken_attempts: int

    def as_dict(self):
        return asdict(self)


class AssessmentLegacyCleanup:
    def inspect(self):
        orphan_exams = GeneratedExam.objects.filter(attempt__isnull=True)
        return LegacyCleanupReport(
            legacy_assignments=0,
            legacy_generated_exams=orphan_exams.count(),
            orphan_generated_exams=orphan_exams.count(),
            orphan_generated_exam_questions=GeneratedExamQuestion.objects.filter(
                exam__isnull=True,
            ).count(),
            broken_attempts=ExamAttempt.objects.filter(generated_exam__isnull=True).count(),
        )

    @transaction.atomic
    def apply(self):
        before = self.inspect()
        ExamAttempt.objects.filter(generated_exam__isnull=True).delete()
        GeneratedExam.objects.filter(attempt__isnull=True).delete()
        return before, self.inspect()
