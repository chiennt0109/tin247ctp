from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from assessment.models import BankQuestion, ExamAttempt, ExamBlueprint, GeneratedExam
from assessment.services.exam_generator import ExamGenerator
from assessment.services.phase4_cleanup import Phase4LegacyCleanup
from assessment.tests.test_exam_generation import ExamGenerationTests


class Phase4CleanupTests(TestCase):
    setUp = ExamGenerationTests.setUp
    create_question = staticmethod(ExamGenerationTests.create_question)
    create_session = ExamGenerationTests.create_session
    lock_versions = ExamGenerationTests.lock_versions

    def create_expired_preview(self):
        self.lock_versions()
        return ExamGenerator().generate_preview(
            self.create_session(), code="PREVIEW", seed="preview", expires_at=timezone.now() - timedelta(seconds=1),
        )

    def test_dry_run_detects_without_writing_and_preserves_core_data(self):
        user = get_user_model().objects.create_user("preserved")
        preview = self.create_expired_preview()
        bank_count = BankQuestion.objects.count()
        blueprint_count = ExamBlueprint.objects.count()

        report = Phase4LegacyCleanup().inspect()

        self.assertEqual(report.legacy_generated_exams, 1)
        self.assertEqual(report.legacy_preview_exams, 1)
        self.assertTrue(GeneratedExam.objects.filter(pk=preview.pk).exists())
        self.assertEqual(BankQuestion.objects.count(), bank_count)
        self.assertEqual(ExamBlueprint.objects.count(), blueprint_count)
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertFalse(ExamAttempt.objects.exists())

    def test_attempt_exam_without_attempt_is_reported_as_orphan(self):
        exam = self.create_expired_preview()
        exam.purpose = GeneratedExam.Purpose.ATTEMPT
        exam.expires_at = None
        exam.save(update_fields=("purpose", "expires_at"))

        report = Phase4LegacyCleanup().inspect()

        self.assertEqual(report.orphan_generated_exams, 1)
        self.assertEqual(report.legacy_generated_exams, 1)

    def test_apply_is_idempotent_and_removes_exam_children_only(self):
        self.create_expired_preview()
        bank_count = BankQuestion.objects.count()
        cleanup = Phase4LegacyCleanup()

        cleanup.apply()
        _before, after = cleanup.apply()

        self.assertFalse(GeneratedExam.objects.exists())
        self.assertEqual(after.legacy_generated_exams, 0)
        self.assertEqual(BankQuestion.objects.count(), bank_count)
