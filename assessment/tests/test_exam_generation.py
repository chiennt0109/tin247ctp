from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from assessment.models import (
    BankQuestion, BankQuestionRevision, BlueprintSection, BlueprintSlot, BlueprintVersion,
    CurriculumNode, CurriculumOutcome,
    ExamBlueprint, ExamSession, GeneratedExam, ScoringRule, ScoringScheme,
    ScoringSchemeVersion,
)
from assessment.services.exam_generator import ExamGenerationError, ExamGenerator
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.exam_session import publish_exam_session
from assessment.services.protected_payload import decrypt_json


class ExamGenerationTests(TestCase):
    def setUp(self):
        blueprint = ExamBlueprint.objects.create(
            name="BP", exam_type="GRADUATION", grade=12,
            status=ExamBlueprint.Status.APPROVED, is_ready=True,
        )
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
        curriculum, _ = CurriculumNode.objects.get_or_create(
            source_id="TEST-CURRICULUM", defaults={
                "grade": 12, "subject": "Tin học", "program_version": "2018",
                "topic_code": "TEST", "topic_name": "Test", "source_status": "ACTIVE",
            },
        )
        outcome, _ = CurriculumOutcome.objects.get_or_create(
            source_id="TEST-OUTCOME", defaults={
                "curriculum": curriculum, "code": "TEST", "text": "Test",
                "cognitive_level": "BIET", "source_status": "ACTIVE",
            },
        )
        question = BankQuestion.objects.create(
            source_question_id=question_id, question_type="MCQ_SINGLE", cognitive_level="BIET",
            difficulty=1, source_status="ACTIVE", process_status="READY_FOR_GRADUATION",
            use_purpose="GRADUATION", shuffle_allowed=True, duplicate_family_id=family,
            content_hash=question_id.ljust(64, "0")[:64], is_available=True,
            nls_frame="TT02_2025", nls_level="NANG_CAO_1", grad_nls_task="PASS",
            graduation_gate="PASS",
            curriculum=curriculum, outcome=outcome,
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

    def create_session(self, slug="exam"):
        now = timezone.now()
        return ExamSession.objects.create(
            slug=slug, name=slug, exam_type=ExamSession.ExamType.GRADUATION,
            blueprint_version=self.blueprint_version, scoring_version=self.scoring_version,
            opens_at=now + timedelta(hours=1), closes_at=now + timedelta(days=1),
            duration_minutes=50,
        )

    def lock_versions(self):
        self.blueprint_version.is_locked = True
        self.blueprint_version.save(update_fields=("is_locked",))
        self.scoring_version.is_locked = True
        self.scoring_version.save(update_fields=("is_locked",))

    def test_seed_reproduces_selection_and_snapshots_hide_plain_answer(self):
        self.lock_versions()
        first = ExamGenerator().generate_for_attempt(self.create_session("one"), code="001", seed="stable")
        second = ExamGenerator().generate_for_attempt(self.create_session("two"), code="001", seed="stable")
        first_ids = list(first.questions.values_list("question_id_snapshot", flat=True))
        second_ids = list(second.questions.values_list("question_id_snapshot", flat=True))
        self.assertEqual(first_ids, second_ids)
        snapshot = first.questions.first()
        self.assertNotIn("answer_key", snapshot.protected_answer_snapshot)
        self.assertEqual(decrypt_json(snapshot.protected_answer_snapshot), {"answer_key": "A"})

    def test_snapshot_does_not_change_when_bank_revision_changes(self):
        self.lock_versions()
        exam = ExamGenerator().generate_for_attempt(self.create_session(), code="001", seed="snapshot")
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
            ExamGenerator().generate_for_attempt(self.create_session(), code="001", seed="family")
        self.assertEqual(GeneratedExam.objects.count(), 0)

    def test_required_nls_metadata_excludes_incompatible_questions(self):
        self.slot.required_tags = {"NLS_PRIMARY": "NLS-X"}
        self.slot.quantity = 1
        self.slot.save(update_fields=("required_tags", "quantity"))
        BankQuestion.objects.update(source_metadata={"NLS_PRIMARY": "NLS-Y"})
        report = BlueprintValidator().validate(self.blueprint_version)
        self.assertEqual(report["availability"][0]["candidates"], 0)

    def test_true_false_statement_order_is_seeded_and_snapshotted(self):
        self.slot.question_type = "TRUE_FALSE_GROUP"
        self.slot.quantity = 1
        self.slot.requires_graduation_eligibility = True
        self.slot.save(update_fields=("question_type", "quantity", "requires_graduation_eligibility"))
        BankQuestion.objects.update(question_type="TRUE_FALSE_GROUP")
        for question in BankQuestion.objects.select_related("current_revision"):
            revision = question.current_revision
            revision.statements = [{"label": label, "text": label} for label in "ABCD"]
            revision.save(update_fields=("statements",))
        self.blueprint_version.expected_question_count = 1
        self.blueprint_version.expected_total_score = Decimal("0.250")
        self.blueprint_version.save(update_fields=("expected_question_count", "expected_total_score"))
        self.lock_versions()
        exam = ExamGenerator().generate_for_attempt(self.create_session(), code="tf", seed="stable")
        item = exam.questions.get()
        self.assertEqual(sorted(item.statement_order), [0, 1, 2, 3])
        self.assertEqual(item.statement_order, [0, 1, 2, 3])
        self.assertEqual(
            item.statements_snapshot,
            [item.bank_revision.statements[index] for index in item.statement_order],
        )

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
