from problems.models import ProblemEditorial, EditorialPurchase
from contests.models import ContestEditorialAccess
from django.utils import timezone


def resolve_editorial_access(user, problem, contest=None, is_practice=False):
    """
    Trả về:
        can_view (bool)
        requires_payment (bool)
        editorial_content (str hoặc None)
        editorial_format (html/md)
    """

    # ============================================================
    # 1) LẤY META EDITORIAL
    # ============================================================
    try:
        meta = ProblemEditorial.objects.get(problem=problem)
        editorial = meta.content
        editorial_format = getattr(meta, "format", "md")
        access_mode = (meta.access_mode or "").strip().lower()
    except ProblemEditorial.DoesNotExist:
        return False, False, None, None

    # ============================================================
    # 2) PRACTICE MODE → CẤM HOÀN TOÀN
    # ============================================================
    if is_practice:
        return False, False, None, None

    # ============================================================
    # 3) CONTEST MODE
    # ============================================================
    if contest:
        now = timezone.now()

        # ❌ A. Contest đang diễn ra → cấm xem hoàn toàn
        if now < contest.end_time:
            return False, False, None, None

        # 🔍 B. Contest đã kết thúc → xét theo RULE
        rule = ContestEditorialAccess.objects.filter(
            contest=contest,
            problem=problem
        ).first()

        if rule:
            mode = rule.mode

            # 1. Ẩn hoàn toàn
            if mode == ContestEditorialAccess.MODE_CONTEST_HIDDEN:
                return False, False, None, None

            # 2. Chỉ xem được sau contest (đang là sau contest rồi)
            if mode == ContestEditorialAccess.MODE_SHOW_AFTER_CONTEST:
                return True, False, editorial, editorial_format

            # 3. Free trong contest → nhưng hiện tại là sau contest → vẫn free
            if mode == ContestEditorialAccess.MODE_SHOW_ONLY_FREE:
                return True, False, editorial, editorial_format

            # 4. Paid-only
            if mode == ContestEditorialAccess.MODE_SHOW_PAID_ONLY:
                if EditorialPurchase.objects.filter(user=user, problem=problem).exists():
                    return True, False, editorial, editorial_format
                else:
                    return False, True, None, None

        # ✔ Nếu KHÔNG có rule → fallback sang NORMAL mode

    # ============================================================
    # 4) NORMAL MODE (ngoài contest hoặc fallback)
    # ============================================================

    # FREE → xem ngay
    if access_mode == "free":
        return True, False, editorial, editorial_format

    # PAID → đã mua thì xem
    if user.is_authenticated:
        if EditorialPurchase.objects.filter(user=user, problem=problem).exists():
            return True, False, editorial, editorial_format

    # Chưa có quyền → phải mua
    return False, True, None, editorial_format
