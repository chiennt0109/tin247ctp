from dataclasses import dataclass

from assessment.models import ExamAccessGrant, ExamSession


@dataclass(frozen=True)
class EffectiveExamAccess:
    allowed: bool
    max_attempts: int | None = None
    valid_until: object | None = None
    grant_id: int | None = None
    reason: str = ""


def _grant_access(grant, now):
    if not grant or not grant.is_active:
        return EffectiveExamAccess(False, reason="Tài khoản chưa được cấp quyền làm kỳ kiểm tra này.")
    uses_time = grant.limit_mode in {
        ExamAccessGrant.LimitMode.VALIDITY, ExamAccessGrant.LimitMode.BOTH,
    }
    if uses_time and (now < grant.valid_from or now >= grant.valid_until):
        return EffectiveExamAccess(False, reason="Quyền làm bài chưa có hiệu lực hoặc đã hết hạn.")
    uses_attempts = grant.limit_mode in {
        ExamAccessGrant.LimitMode.ATTEMPTS, ExamAccessGrant.LimitMode.BOTH,
    }
    return EffectiveExamAccess(
        True,
        max_attempts=grant.max_attempts if uses_attempts else None,
        valid_until=grant.valid_until if uses_time else None,
        grant_id=grant.pk,
    )


def resolve_exam_access(user, session, now, user_grade=None):
    """Resolve access once; a user grant intentionally overrides group grants."""
    if session.access_mode == ExamSession.AccessMode.ACCESS_GRANTS:
        grants = ExamAccessGrant.objects.filter(session=session, is_active=True)
        direct = grants.filter(user=user).first()
        if direct:
            return _grant_access(direct, now)
        group_grants = grants.filter(
            group__in=user.groups.all(), user__isnull=True,
        ).order_by("pk")
        denied = None
        for group_grant in group_grants:
            resolved = _grant_access(group_grant, now)
            if resolved.allowed:
                return resolved
            denied = resolved
        return denied or _grant_access(None, now)
    if session.access_mode == ExamSession.AccessMode.ALL_USERS:
        return EffectiveExamAccess(True, max_attempts=session.max_attempts)
    if session.access_mode == ExamSession.AccessMode.SELECTED_GROUPS:
        allowed = session.access_groups.filter(pk__in=user.groups.values("pk")).exists()
    elif session.access_mode == ExamSession.AccessMode.SELECTED_GRADES:
        allowed = user_grade in {str(value) for value in session.access_grades}
    else:
        allowed = False
    return EffectiveExamAccess(
        allowed, max_attempts=session.max_attempts,
        reason="" if allowed else "Tài khoản không có quyền làm kỳ kiểm tra này.",
    )
