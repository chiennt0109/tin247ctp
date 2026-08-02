from django.core.management import call_command
from django.test import TestCase


class AssessmentSchemaCheckTests(TestCase):
    def test_current_migrated_schema_passes_deployment_check(self):
        call_command("check_assessment_schema")
