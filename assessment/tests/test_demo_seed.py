from itertools import cycle
from importlib import import_module

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from assessment.models import (
    BankQuestion, BankQuestionRevision, ExamBlueprint, ExamParticipant, ExamSession,
    GeneratedExam, ScoringScheme,
)
from assessment.tests.test_bank_importer import WorkbookFactory


class AssessmentDemoSeedTests(TestCase):
    def setUp(self):
        self.workbook = WorkbookFactory.create()
        self.addCleanup(self.workbook.unlink)
        self.student = get_user_model().objects.create_user("demo_student", password="test")
        self.teacher = get_user_model().objects.create_superuser("demo_teacher", "teacher@example.com", "test")
        self._create_pool("READY_FOR_PRACTICE", 12, "P")
        self._create_pool("READY_FOR_PERIODIC", 24, "D")
        self._create_pool("READY_FOR_GRADUATION", 30, "G")

    @staticmethod
    def _create_pool(process_status, count, prefix):
        levels = cycle(("BIET", "HIEU", "VANDUNG"))
        for index in range(count):
            level = next(levels)
            difficulty = index % 5 + 1
            question_id = f"{prefix}{index:03d}"
            question = BankQuestion.objects.create(
                source_question_id=question_id, question_type="MCQ_SINGLE",
                cognitive_level=level, difficulty=difficulty, source_status="ACTIVE",
                process_status=process_status,
                use_purpose=process_status.removeprefix("READY_FOR_"),
                shuffle_allowed=True, duplicate_family_id=f"{prefix}-F-{index}",
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

    def seed(self, *extra):
        call_command(
            "seed_assessment_demo", "--source", str(self.workbook), "--student", "demo_student",
            "--teacher", "demo_teacher", *extra, verbosity=0,
        )

    def test_apply_creates_demo_flow_and_permissions(self):
        self.seed("--apply")
        self.assertEqual(ExamBlueprint.objects.filter(is_demo=True).count(), 3)
        self.assertEqual(ScoringScheme.objects.filter(is_demo=True).count(), 3)
        self.assertEqual(ExamSession.objects.filter(is_demo=True).count(), 4)
        self.assertEqual(ExamSession.objects.filter(demo_key__isnull=False).count(), 4)
        self.assertEqual(ExamParticipant.objects.filter(user=self.student).count(), 4)
        access = ExamParticipant.objects.get(session__slug="assessment-demo-access", user=self.student)
        self.assertTrue(access.can_download_exam)
        self.assertTrue(access.can_download_blueprint)
        practice = ExamParticipant.objects.get(session__slug="assessment-demo-practice", user=self.student)
        self.assertTrue(practice.can_view_answers)
        self.assertEqual(practice.max_attempts_override, 3)

    def test_seed_does_not_pre_generate_student_exams(self):
        self.seed("--apply")
        practice = ExamSession.objects.get(slug="assessment-demo-practice")
        periodic = ExamSession.objects.get(slug="assessment-demo-periodic")
        self.assertEqual(practice.generated_exams.count(), 0)
        self.assertEqual(periodic.generated_exams.count(), 0)
        graduation = ExamSession.objects.get(slug="assessment-demo-graduation")
        # Fixture has no master BLUEPRINTS/BLUEPRINT_CELLS rows, so graduation
        # remains safely in draft rather than filling with practice questions.
        self.assertEqual(graduation.status, ExamSession.Status.DRAFT)
        self.assertFalse(graduation.generated_exams.exists())

    def test_second_apply_is_idempotent(self):
        self.seed("--apply")
        counts = (
            ExamBlueprint.objects.filter(is_demo=True).count(),
            ScoringScheme.objects.filter(is_demo=True).count(),
            ExamSession.objects.filter(is_demo=True).count(), GeneratedExam.objects.count(),
        )
        self.seed("--apply")
        self.assertEqual(counts, (
            ExamBlueprint.objects.filter(is_demo=True).count(),
            ScoringScheme.objects.filter(is_demo=True).count(),
            ExamSession.objects.filter(is_demo=True).count(), GeneratedExam.objects.count(),
        ))

    def test_reset_recreates_demo_without_deleting_bank_or_users(self):
        self.seed("--apply")
        bank_count = BankQuestion.objects.count()
        user_ids = set(get_user_model().objects.values_list("pk", flat=True))
        self.seed("--reset")
        self.assertEqual(BankQuestion.objects.count(), bank_count)
        self.assertEqual(set(get_user_model().objects.values_list("pk", flat=True)), user_ids)
        self.assertEqual(ExamBlueprint.objects.filter(is_demo=True).count(), 3)

    def test_dry_run_does_not_create_demo_data(self):
        self.seed("--dry-run")
        self.assertFalse(ExamBlueprint.objects.filter(is_demo=True).exists())
        self.assertFalse(ExamSession.objects.filter(is_demo=True).exists())

    def test_demo_key_allows_multiple_nulls_and_real_rows_default_false(self):
        first = ExamBlueprint.objects.create(name="Real A", exam_type="PERIODIC", grade=12)
        second = ExamBlueprint.objects.create(name="Real B", exam_type="PERIODIC", grade=12)

        self.assertIsNone(first.demo_key)
        self.assertIsNone(second.demo_key)
        self.assertFalse(first.is_demo)
        self.assertFalse(second.is_demo)

    def test_apply_adopts_legacy_demo_session_without_duplicate(self):
        self.seed("--apply")
        session = ExamSession.objects.get(slug="assessment-demo-practice")
        session.demo_key = None
        session.save(update_fields=("demo_key",))

        self.seed("--apply")

        self.assertEqual(ExamSession.objects.filter(slug=session.slug).count(), 1)
        session.refresh_from_db()
        self.assertEqual(session.demo_key, session.slug)

    def test_restore_migration_backfills_only_known_demo_sessions(self):
        self.seed("--apply")
        demo_session = ExamSession.objects.get(slug="assessment-demo-practice")
        demo_session.demo_key = None
        demo_session.save(update_fields=("demo_key",))
        real_session = ExamSession.objects.get(slug="assessment-demo-periodic")
        real_session.demo_key = None
        real_session.is_demo = False
        real_session.save(update_fields=("demo_key", "is_demo"))

        migration = import_module(
            "assessment.migrations.0006_restore_assessment_demo_and_access_fields"
        )
        migration.backfill_demo_session_keys(apps, None)

        demo_session.refresh_from_db()
        real_session.refresh_from_db()
        self.assertEqual(demo_session.demo_key, demo_session.slug)
        self.assertIsNone(real_session.demo_key)
