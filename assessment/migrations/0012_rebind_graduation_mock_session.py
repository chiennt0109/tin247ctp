from django.db import migrations


def rebind_graduation_mock_session(apps, schema_editor):
    ExamBlueprint = apps.get_model("assessment", "ExamBlueprint")
    ExamSession = apps.get_model("assessment", "ExamSession")
    ScoringSchemeVersion = apps.get_model("assessment", "ScoringSchemeVersion")

    blueprint = ExamBlueprint.objects.filter(name__icontains="TN THPT").order_by("-updated_at", "-pk").first()
    if not blueprint:
        return
    blueprint_version = blueprint.versions.filter(is_locked=True).order_by("-version").first()
    if not blueprint_version:
        return
    candidates = ScoringSchemeVersion.objects.filter(
        is_locked=True, total_score=blueprint_version.expected_total_score,
    ).order_by("-version", "-pk")
    policy_id = str((blueprint_version.source_snapshot or {}).get("POLICY_PROFILE_ID") or "")
    scoring_version = candidates.filter(source_policy_id=policy_id).first() if policy_id else None
    scoring_version = scoring_version or candidates.filter(
        scheme__name=f"{blueprint.name} — Quy tắc chấm"
    ).first()
    if scoring_version:
        ExamSession.objects.filter(name="Thi thử TN THPT").update(
            blueprint_version=blueprint_version, scoring_version=scoring_version,
        )


class Migration(migrations.Migration):
    dependencies = [("assessment", "0011_remove_legacy_generation_architecture")]
    operations = [migrations.RunPython(rebind_graduation_mock_session, migrations.RunPython.noop)]
