from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from assessment.models import (
    BankQuestion, BlueprintSection, BlueprintSlot, BlueprintVersion, ExamAttempt,
    ExamBlueprint, ExamBlueprintGroup, ExamSession, GeneratedExam, ScoringRule,
    ScoringScheme, ScoringSchemeVersion,
)
from assessment.services.start_attempt import StartAttemptError, start_attempt
from assessment.admin import BlueprintGroupForm, ExamSessionAdminForm
from assessment.tests.test_exam_generation import ExamGenerationTests


class EquivalentBlueprintAttemptTests(TestCase):
    create_question = staticmethod(ExamGenerationTests.create_question)

    def setUp(self):
        ExamGenerationTests.setUp(self)
        self.group = ExamBlueprintGroup.objects.create(name="Tốt nghiệp tương đương", code="tn-equivalent")
        self.group.blueprints.add(self.blueprint_version.blueprint)
        self.blueprint_version.is_locked = True
        self.blueprint_version.save(update_fields=("is_locked",))
        self.scoring_version.is_locked = True
        self.scoring_version.scheme.name = f"{self.blueprint_version.blueprint.name} — Quy tắc chấm"
        self.scoring_version.scheme.save(update_fields=("name",))
        self.scoring_version.save(update_fields=("is_locked",))
        self.second_version = self._second_blueprint()
        now = timezone.now()
        self.session = ExamSession.objects.create(
            slug="equivalent-exam", name="Thi thử tương đương", exam_type="GRADUATION",
            blueprint_group=self.group, blueprint_version=self.blueprint_version,
            scoring_version=self.scoring_version, opens_at=now - timedelta(minutes=1),
            closes_at=now + timedelta(hours=1), duration_minutes=50,
            max_attempts=2, status=ExamSession.Status.OPEN,
        )

    def _second_blueprint(self):
        blueprint = ExamBlueprint.objects.create(
            name="BP tương đương 2", exam_type="GRADUATION", grade=12,
        )
        self.group.blueprints.add(blueprint)
        version = BlueprintVersion.objects.create(
            blueprint=blueprint, version=1, duration_minutes=50,
            expected_question_count=2, expected_total_score=Decimal("0.500"), is_locked=True,
        )
        section = BlueprintSection.objects.create(version=version, code="I", name="I")
        BlueprintSlot.objects.create(
            section=section, question_type="MCQ_SINGLE", cognitive_level="BIET",
            quantity=2, score_per_item=Decimal("0.250"),
            requires_graduation_eligibility=True,
        )
        scheme = ScoringScheme.objects.create(name=f"{blueprint.name} — Quy tắc chấm")
        scoring = ScoringSchemeVersion.objects.create(
            scheme=scheme, version=1, total_score=Decimal("0.500"), is_locked=True,
        )
        ScoringRule.objects.create(
            version=scoring, question_type="MCQ_SINGLE", rule_code="MCQ",
            max_score=Decimal("0.250"), configuration={"correct": "0.25"},
        )
        return version

    def test_multiple_ready_blueprints_select_one_and_attempt_records_it(self):
        user = get_user_model().objects.create_user("equivalent-student")
        with patch(
            "assessment.services.start_attempt.secrets.choice",
            side_effect=lambda candidates: candidates[-1],
        ) as choice:
            attempt = start_attempt(user, self.session)
        choice.assert_called_once()
        self.assertIn(attempt.blueprint_id, {
            self.blueprint_version.blueprint_id, self.second_version.blueprint_id,
        })
        self.assertEqual(attempt.blueprint_version_id, attempt.generated_exam.blueprint_version_id)
        self.assertEqual(attempt.blueprint_id, attempt.blueprint_version.blueprint_id)

    def test_later_attempt_uses_an_unused_ready_blueprint_before_repeating(self):
        user = get_user_model().objects.create_user("equivalent-retry")
        first = start_attempt(user, self.session)
        first.status = ExamAttempt.Status.SUBMITTED
        first.save(update_fields=("status",))

        second = start_attempt(user, self.session)

        self.assertNotEqual(first.blueprint_id, second.blueprint_id)
        self.assertEqual(second.blueprint_version_id, second.generated_exam.blueprint_version_id)

    def test_group_form_lists_all_blueprints_and_accepts_shortage(self):
        self.second_version.sections.first().slots.update(quantity=20)
        form = BlueprintGroupForm(data={
            "name": "Nhóm thủ công", "code": "manual-group", "exam_type": "GRADUATION",
            "is_active": True, "selection_policy": "RANDOM_READY",
            "cognitive_tolerance": "0.100", "duration_tolerance_minutes": 0,
            "blueprints": [
                self.blueprint_version.blueprint_id, self.second_version.blueprint_id,
            ],
        })
        self.assertEqual(form.fields["blueprints"].queryset.count(), 2)
        self.assertTrue(form.is_valid(), form.errors)
        group = form.save()
        self.assertEqual(group.blueprints.count(), 2)

    def test_exam_session_form_does_not_reset_blueprint_lock_or_ready_flags(self):
        blueprint_ids = [self.blueprint_version.blueprint_id, self.second_version.blueprint_id]
        ExamBlueprint.objects.filter(pk__in=blueprint_ids).update(is_locked=True, is_ready=True)
        now = timezone.now()
        form = ExamSessionAdminForm(data={
            "name": "Kỳ thi không đổi trạng thái ma trận",
            "blueprint_group": self.group.pk,
            "opens_at": now + timedelta(hours=1),
            "closes_at": now + timedelta(hours=2),
            "duration_minutes": 50, "max_attempts": 1,
            "access_mode": "ALL_USERS", "score_release_mode": "MANUAL_RELEASE",
            "answer_release_mode": "NEVER",
        })
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        states = set(
            ExamBlueprint.objects.filter(pk__in=blueprint_ids)
            .values_list("is_locked", "is_ready")
        )
        self.assertEqual(states, {(True, True)})

    def test_blueprint_with_shortage_is_not_selected(self):
        self.second_version.sections.first().slots.update(quantity=20)
        user = get_user_model().objects.create_user("only-ready")
        attempt = start_attempt(user, self.session)
        self.assertEqual(attempt.blueprint_id, self.blueprint_version.blueprint_id)

    def test_double_click_still_returns_one_attempt_and_exam(self):
        user = get_user_model().objects.create_user("double-equivalent")
        first = start_attempt(user, self.session)
        second = start_attempt(user, self.session)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(ExamAttempt.objects.count(), 1)
        self.assertEqual(GeneratedExam.objects.count(), 1)

    def test_no_ready_blueprint_rolls_back_cleanly(self):
        BankQuestion.objects.update(is_available=False)
        user = get_user_model().objects.create_user("no-ready")
        with self.assertRaisesMessage(StartAttemptError, "Chưa có ma trận đủ nguồn câu để sinh đề"):
            start_attempt(user, self.session)
        self.assertFalse(ExamAttempt.objects.exists())
        self.assertFalse(GeneratedExam.objects.exists())
