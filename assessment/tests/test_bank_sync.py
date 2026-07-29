from django.core.management import call_command
from django.test import TestCase, override_settings
from openpyxl import load_workbook

from assessment.models import BankQuestion, BankQuestionRevision, QuestionAsset, QuestionSyncLog
from assessment.services.bank_importer import WorkbookBankImporter
from assessment.services.bank_sync import BankSyncService
from assessment.tests.test_bank_importer import WorkbookFactory


class BankSyncServiceTests(TestCase):
    def setUp(self):
        self.path = WorkbookFactory.create()
        self.addCleanup(self.path.unlink)

    def test_preview_does_not_write(self):
        parsed = WorkbookBankImporter().parse(self.path)
        report = BankSyncService().preview(parsed)
        self.assertEqual(report["new"], 1)
        self.assertEqual(BankQuestion.objects.count(), 0)
        self.assertEqual(QuestionSyncLog.objects.count(), 0)

    def test_apply_creates_projection_and_unchanged_sync_does_not_add_revision(self):
        parsed = WorkbookBankImporter().parse(self.path)
        BankSyncService().apply(parsed)
        question = BankQuestion.objects.get(source_question_id="Q1")
        self.assertTrue(question.is_available)
        self.assertEqual(question.current_revision.protected_answer, {"answer_key": "A"})
        BankSyncService().apply(WorkbookBankImporter().parse(self.path))
        self.assertEqual(BankQuestionRevision.objects.filter(question=question).count(), 1)

    def test_apply_uses_the_integer_normalized_by_dry_run_pipeline(self):
        numeric_string_path = WorkbookFactory.create(estimated_time="135")
        self.addCleanup(numeric_string_path.unlink)
        parsed = WorkbookBankImporter().parse(numeric_string_path)
        self.assertFalse(parsed.errors)
        self.assertEqual(parsed.questions[0]["estimated_time_seconds"], 135)
        BankSyncService().apply(parsed)
        self.assertEqual(BankQuestion.objects.get().estimated_time_seconds, 135)

    def test_changed_content_creates_revision_and_preserves_old_revision(self):
        BankSyncService().apply(WorkbookBankImporter().parse(self.path))
        workbook = load_workbook(self.path)
        workbook["QUESTIONS"]["E2"] = "Updated stem"
        workbook.save(self.path)
        BankSyncService().apply(WorkbookBankImporter().parse(self.path))
        question = BankQuestion.objects.get(source_question_id="Q1")
        self.assertEqual(question.revisions.count(), 2)
        self.assertEqual(question.current_revision.stem_text, "Updated stem")

    def test_fatal_validation_error_rolls_back_everything(self):
        workbook = load_workbook(self.path)
        workbook["QUESTIONS"]["F2"] = None
        workbook.save(self.path)
        parsed = WorkbookBankImporter().parse(self.path)
        with self.assertRaises(ValueError):
            BankSyncService().apply(parsed)
        self.assertEqual(BankQuestion.objects.count(), 0)
        self.assertEqual(QuestionSyncLog.objects.count(), 0)

    @override_settings(QUESTION_BANK_SYNC_ENABLED=True)
    def test_command_apply_twice_deduplicates_source_and_updates_asset(self):
        duplicate_path = WorkbookFactory.create(duplicate_source=True)
        self.addCleanup(duplicate_path.unlink)

        call_command("sync_exam_bank", "--source", str(duplicate_path), "--apply", verbosity=0)
        asset = QuestionAsset.objects.get()
        original_pk = asset.pk
        self.assertEqual(asset.source_page, "2")
        self.assertEqual(QuestionAsset.objects.count(), 1)

        # A subsequent master update for the same (question, source_file) must
        # update the existing relation rather than attempting another INSERT.
        workbook = load_workbook(duplicate_path)
        workbook["QUESTION_SOURCES"]["D3"] = "3"
        workbook["QUESTION_SOURCES"]["E3"] = "newest-section"
        workbook.save(duplicate_path)
        call_command("sync_exam_bank", "--source", str(duplicate_path), "--apply", verbosity=0)

        asset.refresh_from_db()
        self.assertEqual(asset.pk, original_pk)
        self.assertEqual(asset.source_page, "3")
        self.assertEqual(asset.source_section, "newest-section")
        self.assertEqual(QuestionAsset.objects.count(), 1)
