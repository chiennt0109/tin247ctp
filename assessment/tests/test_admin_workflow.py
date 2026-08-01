from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from assessment.admin import ExamSessionAdminForm
from assessment.models import BankQuestion, ExamSession
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.demo_cleanup import AssessmentDemoCleanup
from assessment.services.session_configuration import resolve_locked_configuration
from assessment.services.admin_workflow import close_exam_session, open_exam_session, prepare_blueprint
from assessment.tests.test_exam_generation import ExamGenerationTests


class AssessmentAdminWorkflowTests(TestCase):
    create_question = staticmethod(ExamGenerationTests.create_question)
    create_session = ExamGenerationTests.create_session
    lock_versions = ExamGenerationTests.lock_versions

    def setUp(self):
        ExamGenerationTests.setUp(self)
        self.lock_versions()
        self.scoring_version.scheme.name = f"{self.blueprint_version.blueprint.name} — Quy tắc chấm"
        self.scoring_version.scheme.save(update_fields=("name",))

    def test_resolver_uses_latest_locked_blueprint_and_matching_scoring(self):
        blueprint_version, scoring_version = resolve_locked_configuration(
            self.blueprint_version.blueprint,
        )
        self.assertEqual(blueprint_version, self.blueprint_version)
        self.assertEqual(scoring_version, self.scoring_version)

    def test_single_prepare_action_locks_blueprint_and_scoring(self):
        type(self.blueprint_version).objects.filter(pk=self.blueprint_version.pk).update(is_locked=False)
        type(self.scoring_version).objects.filter(pk=self.scoring_version.pk).update(is_locked=False)
        prepared = prepare_blueprint(self.blueprint_version.blueprint)
        self.blueprint_version.refresh_from_db()
        self.scoring_version.refresh_from_db()
        self.assertTrue(prepared.is_locked)
        self.assertTrue(prepared.is_ready)
        self.assertTrue(self.blueprint_version.is_locked)
        self.assertTrue(self.scoring_version.is_locked)

    def test_open_and_close_session_are_explicit_workflow_actions(self):
        session = self.create_session("workflow-status")
        now = timezone.now()
        session.opens_at = now - timedelta(minutes=1)
        session.closes_at = now + timedelta(hours=1)
        session.save(update_fields=("opens_at", "closes_at"))
        opened = open_exam_session(session)
        self.assertEqual(opened.status, ExamSession.Status.OPEN)
        closed = close_exam_session(opened)
        self.assertEqual(closed.status, ExamSession.Status.CLOSED)

    def test_admin_form_selects_blueprint_instead_of_internal_versions(self):
        now = timezone.now()
        form = ExamSessionAdminForm(data={
            "blueprint": self.blueprint_version.blueprint_id,
            "slug": "simple-admin", "name": "Simple", "exam_type": "GRADUATION",
            "opens_at": now + timedelta(hours=1), "closes_at": now + timedelta(hours=2),
            "duration_minutes": 50, "max_attempts": 1, "attempt_result_mode": "HIGHEST",
            "next_attempt_delay_minutes": 0, "access_mode": "ALL_USERS",
            "score_release_mode": "MANUAL_RELEASE", "answer_release_mode": "NEVER",
            "solution_release_mode": "NEVER", "status": "DRAFT",
        })
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.blueprint_version, self.blueprint_version)
        self.assertEqual(form.instance.scoring_version, self.scoring_version)

    def test_diagnostic_names_slot_counts_and_exclusion_conditions(self):
        BankQuestion.objects.update(process_status="READY_FOR_PERIODIC")
        report = BlueprintValidator().validate(
            self.blueprint_version, scoring_version=self.scoring_version,
        )
        detail = BlueprintValidator.format_failure(report)
        self.assertIn(f"Slot {self.slot.pk}: cần 2 / có 0", detail)
        self.assertIn("question_type", detail)
        self.assertIn("cognitive_level", detail)
        self.assertIn("eligibility", detail)

    def test_demo_cleanup_removes_only_named_demo_sessions(self):
        demo = self.create_session("demo-access")
        demo.name = "[DEMO] Kiểm tra quyền truy cập"
        demo.save(update_fields=("name",))
        real = self.create_session("real-session")
        real.name = "Thi thử TN THPT"
        real.save(update_fields=("name",))
        before, after = AssessmentDemoCleanup().apply()
        self.assertEqual(before.sessions, 1)
        self.assertEqual(after.sessions, 0)
        self.assertTrue(ExamSession.objects.filter(pk=real.pk).exists())
        self.assertEqual(BankQuestion.objects.count(), 4)

    def test_demo_cleanup_command_dry_run_does_not_delete(self):
        demo = self.create_session("demo-practice")
        demo.name = "[DEMO] Luyện tập tự do"
        demo.save(update_fields=("name",))
        call_command("cleanup_assessment_demo", "--dry-run")
        self.assertTrue(ExamSession.objects.filter(pk=demo.pk).exists())
