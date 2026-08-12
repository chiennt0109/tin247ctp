import subprocess
from unittest.mock import patch

from django.core.management.base import CommandError
from django.test import SimpleTestCase

from assessment.management.commands.reset_assessment_for_bank_v2 import Command


class ResetAssessmentCommandTests(SimpleTestCase):
    def test_backup_process_has_a_hard_timeout(self):
        command = Command()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("pg_dump", 7)):
            with self.assertRaisesMessage(CommandError, "exceeded 7 seconds"):
                command._run_backup_process(
                    ["pg_dump"], env={}, timeout=7, label="pg_dump",
                )

    def test_missing_postgres_binary_aborts_without_purge(self):
        command = Command()
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with self.assertRaisesMessage(CommandError, "executable was not found"):
                command._run_backup_process(
                    ["pg_dump"], env={}, timeout=7, label="pg_dump",
                )
