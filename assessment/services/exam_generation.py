"""Public generation API; implementation lives in the focused generator class."""
from assessment.services.exam_generator import ExamGenerationError, ExamGenerator


def generate_exam_for_attempt(session, user, seed, *, code, blueprint_version=None, scoring_version=None):
    return ExamGenerator().generate_for_attempt(
        session, code=code, seed=seed, actor=user,
        blueprint_version=blueprint_version, scoring_version=scoring_version,
    )

