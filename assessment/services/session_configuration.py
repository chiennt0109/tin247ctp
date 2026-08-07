from django.core.exceptions import ValidationError

from assessment.models import ScoringSchemeVersion
from assessment.services.scoring_versioning import validate_scoring_version


def resolve_locked_configuration(blueprint):
    blueprint_version = blueprint.versions.filter(is_locked=True).order_by("-version").first()
    if blueprint_version is None:
        raise ValidationError(
            f"Ma trận '{blueprint}' chưa có phiên bản đã khóa. Hãy dùng thao tác Khóa phiên bản."
        )

    policy_id = str(blueprint_version.source_snapshot.get("POLICY_PROFILE_ID") or "")
    candidates = ScoringSchemeVersion.objects.filter(
        is_locked=True, total_score=blueprint_version.expected_total_score,
    ).select_related("scheme").order_by("-version", "-pk")
    if policy_id:
        policy_match = candidates.filter(source_policy_id=policy_id).first()
        if policy_match:
            candidates = [policy_match]
    else:
        named = candidates.filter(scheme__name=f"{blueprint.name} — Quy tắc chấm")
        candidates = list(named) or list(candidates)

    for scoring_version in candidates:
        try:
            validate_scoring_version(scoring_version, blueprint_version=blueprint_version)
        except ValidationError:
            continue
        return blueprint_version, scoring_version
    raise ValidationError(
        f"Không có phiên bản quy tắc chấm đã khóa phù hợp với ma trận '{blueprint}' "
        f"({blueprint_version.expected_total_score} điểm)."
    )
