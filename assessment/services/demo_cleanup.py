from dataclasses import asdict, dataclass

from django.db import transaction

from assessment.models import (
    AttemptAnswer, BlueprintVersion, ExamAttempt, ExamBlueprint, ExamSession,
    GeneratedExam, GeneratedExamQuestion, GradingResult, ScoringScheme,
    ScoringSchemeVersion,
)


DEMO_SESSION_NAMES = {"[DEMO] Kiểm tra quyền truy cập", "[DEMO] Luyện tập tự do"}


@dataclass
class DemoCleanupReport:
    sessions: int
    attempts: int
    generated_exams: int
    answers: int
    grading_results: int
    blueprints: int
    scoring_schemes: int

    def as_dict(self):
        return asdict(self)


class AssessmentDemoCleanup:
    @staticmethod
    def sessions():
        return ExamSession.objects.filter(name__in=DEMO_SESSION_NAMES)

    def inspect(self):
        sessions = self.sessions()
        attempts = ExamAttempt.objects.filter(session__in=sessions)
        exams = GeneratedExam.objects.filter(session__in=sessions)
        blueprint_ids = set(sessions.values_list("blueprint_version__blueprint_id", flat=True))
        scoring_ids = set(sessions.values_list("scoring_version__scheme_id", flat=True))
        return DemoCleanupReport(
            sessions=sessions.count(), attempts=attempts.count(), generated_exams=exams.count(),
            answers=AttemptAnswer.objects.filter(attempt__in=attempts).count(),
            grading_results=GradingResult.objects.filter(attempt__in=attempts).count(),
            blueprints=ExamBlueprint.objects.filter(pk__in=blueprint_ids, name__startswith="[DEMO]").count(),
            scoring_schemes=ScoringScheme.objects.filter(pk__in=scoring_ids, name__startswith="[DEMO]").count(),
        )

    @transaction.atomic
    def apply(self):
        before = self.inspect()
        sessions = list(self.sessions())
        attempts = ExamAttempt.objects.filter(session__in=sessions)
        exams = GeneratedExam.objects.filter(session__in=sessions)
        blueprint_ids = {session.blueprint_version.blueprint_id for session in sessions}
        scoring_ids = {session.scoring_version.scheme_id for session in sessions}

        GradingResult.objects.filter(attempt__in=attempts).delete()
        AttemptAnswer.objects.filter(attempt__in=attempts).delete()
        attempts.delete()
        GeneratedExamQuestion.objects.filter(exam__in=exams).delete()
        exams.delete()
        ExamSession.objects.filter(pk__in=[session.pk for session in sessions]).delete()

        for version in BlueprintVersion.objects.filter(
            blueprint_id__in=blueprint_ids, blueprint__name__startswith="[DEMO]",
        ):
            if not version.exam_sessions.exists() and not GeneratedExam.objects.filter(blueprint_version=version).exists():
                version.delete()
        ExamBlueprint.objects.filter(
            pk__in=blueprint_ids, name__startswith="[DEMO]", versions__isnull=True,
        ).delete()
        for version in ScoringSchemeVersion.objects.filter(
            scheme_id__in=scoring_ids, scheme__name__startswith="[DEMO]",
        ):
            if (
                not version.exam_sessions.exists()
                and not GeneratedExam.objects.filter(scoring_version=version).exists()
                and not GradingResult.objects.filter(scoring_version=version).exists()
            ):
                version.delete()
        ScoringScheme.objects.filter(
            pk__in=scoring_ids, name__startswith="[DEMO]", versions__isnull=True,
        ).delete()
        return before, self.inspect()
