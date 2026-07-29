from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from assessment.models import ExamParticipant


@login_required
def exam_list(request):
    """Show only assessment sessions assigned to the signed-in DMOJ user."""
    participations = (
        ExamParticipant.objects.filter(
            user=request.user,
            is_enabled=True,
            can_access=True,
        )
        .select_related("session", "session__blueprint_version")
        .order_by("session__opens_at", "session__name")
    )
    return render(
        request,
        "assessment/exam_list.html",
        {"participations": participations},
    )
