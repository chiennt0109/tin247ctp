import subprocess
from unittest.mock import patch

from django.core.management.base import CommandError
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase
from django.apps import apps

from assessment.management.commands.reset_assessment_for_bank_v2 import Command


class ResetAssessmentCommandTests(SimpleTestCase):
    def test_purge_list_contains_every_assessment_model_only(self):
        from assessment.management.commands.reset_assessment_for_bank_v2 import PURGE_MODELS

        expected = set(apps.get_app_config("assessment").get_models())
        self.assertEqual(set(PURGE_MODELS), expected)
        self.assertTrue(all(model._meta.app_label == "assessment" for model in PURGE_MODELS))

    def test_backup_process_has_a_hard_timeout(self):
        command = Command()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pg_dump", 7)):
            with self.assertRaisesMessage(CommandError, "exceeded 7 seconds"):
                command._run_backup_process(
                    ["pg_dump"], env={}, timeout=7, label="pg_dump",
                )


class ResetAssessmentApplyTests(TestCase):
    def test_no_backup_deletes_assessment_only_and_preserves_user(self):
        from assessment.models import AssessmentAuditLog, TrialAccountLink, TrialEntitlement

        user = get_user_model().objects.create_user("preserved-user")
        entitlement = TrialEntitlement.objects.create()
        TrialAccountLink.objects.create(entitlement=entitlement, user=user)
        AssessmentAuditLog.objects.create(action="OLD", actor=user)

        with patch.object(Command, "_backup") as backup:
            call_command("reset_assessment_for_bank_v2", "--apply", "--no-backup", verbosity=0)

        backup.assert_not_called()
        self.assertTrue(get_user_model().objects.filter(pk=user.pk).exists())
        self.assertFalse(TrialEntitlement.objects.exists())
        self.assertFalse(AssessmentAuditLog.objects.exists())

    def test_missing_postgres_binary_aborts_without_purge(self):
        command = Command()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesMessage(CommandError, "executable was not found"):
                command._run_backup_process(
                    ["pg_dump"], env={}, timeout=7, label="pg_dump",
                )
