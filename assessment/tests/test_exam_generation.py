from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from assessment.models import (
    BankQuestion, BankQuestionRevision, BlueprintSection, BlueprintSlot, BlueprintVersion,
    ExamBlueprint, ExamSession, GeneratedExam, ScoringRule, ScoringScheme,
    ScoringSchemeVersion,
)
from assessment.services.exam_generator import ExamGenerationError, ExamGenerator
from assessment.services.exam_session import publish_exam_session
from assessment.services.protected_payload import decrypt_json


class ExamGenerationTests(TestCase):
    def setUp(self):
        blueprint = ExamBlueprint.objects.create(name="BP", exam_type="GRADUATION", grade=12)
        self.blueprint_version = BlueprintVersion.objects.create(
            blueprint=blueprint, version=1, duration_minutes=50,
            expected_question_count=2, expected_total_score=Decimal("0.500"),
        )
        section = BlueprintSection.objects.create(version=self.blueprint_version, code="I", name="I")
        self.slot = BlueprintSlot.objects.create(
            section=section, question_type="MCQ_SINGLE", cognitive_level="BIET",
            quantity=2, score_per_item=Decimal("0.250"),
            requires_graduation_eligibility=True,
        )
        scheme = ScoringScheme.objects.create(name="Score")
        self.scoring_version = ScoringSchemeVersion.objects.create(
            scheme=scheme, version=1, total_score=Decimal("0.500"),
        )
        ScoringRule.objects.create(
            version=self.scoring_version, question_type="MCQ_SINGLE", rule_code="MCQ",
            max_score=Decimal("0.250"), configuration={"correct": "0.25", "incorrect": "0"},
        )
        for index in range(1, 5):
            self.create_question(f"Q{index}", family=f"F{index}")

    @staticmethod
    def create_question(question_id, family):
        question = BankQuestion.objects.create(
            source_question_id=question_id, question_type="MCQ_SINGLE", cognitive_level="BIET",
            difficulty=1, source_status="ACTIVE", process_status="READY_FOR_GRADUATION",
            use_purpose="GRADUATION", shuffle_allowed=True, duplicate_family_id=family,
            content_hash=question_id.ljust(64, "0")[:64], is_available=True,
        )
        revision = BankQuestionRevision.objects.create(
            question=question, source_version="1", content_hash=question.content_hash,
            stem_text=f"Stem {question_id}",
            options=[{"label": label, "text": label} for label in "ABCD"],
            protected_answer={"answer_key": "A"},
        )
        question.current_revision = revision
        question.save(update_fields=("current_revision",))
        return question

    def create_session(self, slug="exam", mode=ExamSession.GenerationMode.ON_DEMAND_INDIVIDUAL, code_count=1):
        now = timezone.now()
        return ExamSession.objects.create(
            slug=slug, name=slug, exam_type=ExamSession.ExamType.GRADUATION,
            blueprint_version=self.blueprint_version, scoring_version=self.scoring_version,
            opens_at=now + timedelta(hours=1), closes_at=now + timedelta(days=1),
            duration_minutes=50, generation_mode=mode, code_count=code_count,
        )

    def lock_versions(self):
        self.blueprint_version.is_locked = True
        self.blueprint_version.save(update_fields=("is_locked",))
        self.scoring_version.is_locked = True
        self.scoring_version.save(update_fields=("is_locked",))

    def test_seed_reproduces_selection_and_snapshots_hide_plain_answer(self):
        self.lock_versions()
        first = ExamGenerator().generate_preview(self.create_session("one"), code="001", seed="stable", expires_at=timezone.now() + timedelta(minutes=5))
        second = ExamGenerator().generate_preview(self.create_session("two"), code="001", seed="stable", expires_at=timezone.now() + timedelta(minutes=5))
        first_ids = list(first.questions.values_list("question_id_snapshot", flat=True))
        second_ids = list(second.questions.values_list("question_id_snapshot", flat=True))
        self.assertEqual(first_ids, second_ids)
        snapshot = first.questions.first()
        self.assertNotIn("answer_key", snapshot.protected_answer_snapshot)
        self.assertEqual(decrypt_json(snapshot.protected_answer_snapshot), {"answer_key": "A"})

    def test_snapshot_does_not_change_when_bank_revision_changes(self):
        self.lock_versions()
        exam = ExamGenerator().generate_preview(self.create_session(), code="001", seed="snapshot", expires_at=timezone.now() + timedelta(minutes=5))
        item = exam.questions.first()
        original_stem = item.stem_snapshot
        revision = item.bank_question.current_revision
        revision.stem_text = "Changed in bank"
        revision.save(update_fields=("stem_text",))
        item.refresh_from_db()
        self.assertEqual(item.stem_snapshot, original_stem)

    def test_generator_never_selects_two_questions_from_same_family(self):
        BankQuestion.objects.update(duplicate_family_id="ONE-FAMILY")
        self.lock_versions()
        with self.assertRaises(ExamGenerationError):
            ExamGenerator().generate_preview(self.create_session(), code="001", seed="family", expires_at=timezone.now() + timedelta(minutes=5))
        self.assertEqual(GeneratedExam.objects.count(), 0)

    def test_publish_locks_versions_without_pre_generating_exams(self):
        session = self.create_session("publish")
        published = publish_exam_session(session)
        self.assertEqual(published.status, ExamSession.Status.SCHEDULED)
        self.assertFalse(GeneratedExam.objects.filter(session=session).exists())
        self.blueprint_version.refresh_from_db()
        self.scoring_version.refresh_from_db()
        self.assertTrue(self.blueprint_version.is_locked)
        self.assertTrue(self.scoring_version.is_locked)

    def test_invalid_session_window_is_rejected(self):
        session = self.create_session()
        session.closes_at = session.opens_at
        with self.assertRaises(ValidationError):
            session.full_clean()
