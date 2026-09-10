from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q

from submissions.models import Submission

from .models import Contest, Participation, PracticeSession


@dataclass(frozen=True)
class ContestResetResult:
    submissions: int
    participations: int
    practice_sessions: int


@transaction.atomic
def reset_contest_results(contest: Contest) -> ContestResetResult:
    """Delete every result belonging to one contest, without deleting its setup."""
    submissions = Submission.objects.filter(
        Q(contest=contest) | Q(practice_session__contest=contest)
    )
    submission_count = submissions.count()
    submissions.delete()

    participation_count = Participation.objects.filter(contest=contest).count()
    Participation.objects.filter(contest=contest).delete()

    practice_session_count = PracticeSession.objects.filter(contest=contest).count()
    PracticeSession.objects.filter(contest=contest).delete()

    return ContestResetResult(
        submissions=submission_count,
        participations=participation_count,
        practice_sessions=practice_session_count,
    )
