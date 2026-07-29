from django.test import TestCase
from openpyxl import load_workbook

from assessment.models import BankQuestion, BankQuestionRevision, QuestionSyncLog
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
