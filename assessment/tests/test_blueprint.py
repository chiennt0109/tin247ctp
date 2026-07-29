from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from assessment.models import (
    AssessmentAuditLog, BankQuestion, BlueprintSection, BlueprintSlot, BlueprintVersion, ExamBlueprint,
    ScoringRule, ScoringScheme, ScoringSchemeVersion,
)
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.blueprint_versioning import clone_blueprint_version, lock_blueprint_version


class BlueprintTests(TestCase):
    def setUp(self):
        self.blueprint = ExamBlueprint.objects.create(
            name="Ma trận 12", exam_type="GRADUATION", grade=12,
        )
        self.version = BlueprintVersion.objects.create(
            blueprint=self.blueprint, version=1, duration_minutes=50,
            expected_question_count=2, expected_total_score=Decimal("0.500"),
        )
        self.section = BlueprintSection.objects.create(
            version=self.version, code="I", name="Phần I", order=1,
        )
        self.slot = BlueprintSlot.objects.create(
            section=self.section, order=1, question_type="MCQ_SINGLE",
            cognitive_level="BIET", quantity=2, score_per_item=Decimal("0.250"),
            requires_graduation_eligibility=True,
        )
        self.scheme = ScoringScheme.objects.create(name="Chấm tốt nghiệp")
        self.scoring_version = ScoringSchemeVersion.objects.create(
            scheme=self.scheme, version=1, total_score=Decimal("0.500"),
        )
        ScoringRule.objects.create(
            version=self.scoring_version, question_type="MCQ_SINGLE",
            rule_code="MCQ_SINGLE", max_score=Decimal("0.250"),
            configuration={"correct": "0.25", "incorrect": "0"},
        )

    @staticmethod
    def create_question(question_id, family=""):
        return BankQuestion.objects.create(
            source_question_id=question_id, question_type="MCQ_SINGLE",
            cognitive_level="BIET", difficulty=1, source_status="ACTIVE",
            process_status="READY_FOR_GRADUATION", use_purpose="GRADUATION",
            content_hash=question_id.ljust(64, "0")[:64], is_available=True,
            duplicate_family_id=family,
        )

    def test_validator_accepts_totals_inventory_and_scoring_coverage(self):
        self.create_question("Q1")
        self.create_question("Q2")
        self.create_question("Q3")
        report = BlueprintValidator().validate(self.version, scoring_version=self.scoring_version)
        self.assertTrue(report["valid"])
        self.assertEqual(report["question_total"], 2)
        self.assertEqual(report["score_total"], "0.500")
        self.assertEqual(report["availability"][0]["status"], "TIGHT")

    def test_validator_rejects_duplicate_family_capacity(self):
        self.create_question("Q1", family="FAMILY-A")
        self.create_question("Q2", family="FAMILY-A")
        report = BlueprintValidator().validate(self.version, scoring_version=self.scoring_version)
        self.assertFalse(report["valid"])
        self.assertEqual(report["error_counts"]["INSUFFICIENT_DISTINCT_FAMILIES"], 1)

    def test_validator_rejects_missing_scoring_rule(self):
        self.create_question("Q1")
        self.create_question("Q2")
        empty_scheme = ScoringScheme.objects.create(name="Empty")
        empty_version = ScoringSchemeVersion.objects.create(
            scheme=empty_scheme, version=1, total_score=Decimal("0.500"),
        )
        report = BlueprintValidator().validate(self.version, scoring_version=empty_version)
        self.assertEqual(report["error_counts"]["MISSING_SCORING_RULE"], 1)

    def test_clone_creates_editable_new_version_with_sections_and_slots(self):
        clone = clone_blueprint_version(self.version)
        self.assertEqual(clone.version, 2)
        self.assertFalse(clone.is_locked)
        self.assertEqual(clone.sections.count(), 1)
        self.assertEqual(clone.sections.get().slots.count(), 1)
        self.assertTrue(AssessmentAuditLog.objects.filter(action="CLONE_BLUEPRINT_VERSION").exists())

    def test_lock_validates_and_prevents_future_version_edits(self):
        self.create_question("Q1")
        self.create_question("Q2")
        lock_blueprint_version(self.version, scoring_version=self.scoring_version)
        self.version.refresh_from_db()
        self.assertTrue(self.version.is_locked)
        self.assertTrue(AssessmentAuditLog.objects.filter(action="LOCK_BLUEPRINT_VERSION").exists())
        self.version.duration_minutes = 60
        with self.assertRaises(ValidationError):
            self.version.save()

    def test_locked_slot_rejects_model_validation(self):
        self.version.is_locked = True
        self.version.save(update_fields=("is_locked",))
        self.slot.quantity = 3
        with self.assertRaises(ValidationError):
            self.slot.full_clean()

    def test_validator_rejects_total_mismatches(self):
        self.version.expected_question_count = 3
        self.version.expected_total_score = Decimal("1.000")
        self.version.save()
        report = BlueprintValidator().validate(self.version, scoring_version=self.scoring_version)
        self.assertEqual(report["error_counts"]["QUESTION_TOTAL_MISMATCH"], 1)
        self.assertEqual(report["error_counts"]["SCORE_TOTAL_MISMATCH"], 1)
