from django.core.management import call_command
from django.test import SimpleTestCase

from assessment.tests import REMOVED_TEST_MODULES


class AssessmentSourceHygieneTests(SimpleTestCase):
    def test_removed_legacy_modules_are_excluded_from_canonical_discovery(self):
        self.assertEqual(REMOVED_TEST_MODULES, {"test_demo_seed", "test_phase4_cleanup"})

    def test_source_check_command_runs(self):
        call_command("check_assessment_source")
