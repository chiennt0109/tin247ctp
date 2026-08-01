from types import SimpleNamespace

from django.test import TestCase

from assessment.models import ExamBlueprint, ExamBlueprintGroup
from assessment.services.configuration_sync import MasterConfigurationSync


class MasterConfigurationSyncTests(TestCase):
    def test_approved_regular_grade_blueprints_are_real_and_idempotent(self):
        parsed = SimpleNamespace(rows={
            "BLUEPRINTS": [{
                "BLUEPRINT_ID": f"TX-{grade}", "BLUEPRINT_NAME": f"Kiểm tra thường xuyên khối {grade}",
                "EXAM_TYPE": "REGULAR", "GRADE": grade, "SUBJECT": "Tin học",
                "TOTAL_QUESTIONS": 1, "TOTAL_SCORE": "1", "DURATION_MIN": 15,
                "VERSION": 1, "STATUS": "APPROVED", "SEMESTER": "1",
                "POLICY_PROFILE_ID": "TX", "NOTE": "",
                "EQUIVALENCE_GROUP": "TX-EQUIVALENT",
            } for grade in (10, 11, 12)],
            "BLUEPRINT_CELLS": [{
                "BLUEPRINT_CELL_ID": f"CELL-{grade}", "BLUEPRINT_ID": f"TX-{grade}",
                "CURRICULUM_ID": "", "OUTCOME_ID": "", "QUESTION_TYPE": "MCQ_SINGLE",
                "COGNITIVE_LEVEL": "BIET", "REQUIRED_COUNT": 1, "SCORE_PER_ITEM": "1",
                "STATUS": "APPROVED", "DIFFICULTY": None, "COMPETENCY": "",
            } for grade in (10, 11, 12)],
            "SCORE_RULES": [{
                "POLICY_PROFILE_ID": "TX", "QUESTION_TYPE": "MCQ_SINGLE",
                "RULE_CODE": "TX-MCQ", "MAX_SCORE": "1", "STATUS": "APPROVED",
            }],
        })

        first = MasterConfigurationSync().apply(parsed)
        second = MasterConfigurationSync().apply(parsed)

        self.assertEqual(first["created"], 3)
        self.assertEqual(second["created"], 0)
        self.assertEqual(ExamBlueprint.objects.count(), 3)
        self.assertEqual(set(ExamBlueprint.objects.values_list("grade", flat=True)), {10, 11, 12})
        self.assertEqual(ExamBlueprintGroup.objects.count(), 1)
        self.assertEqual(ExamBlueprintGroup.objects.get().blueprints.count(), 3)
        self.assertFalse(ExamBlueprint.objects.filter(name__startswith="[DEMO]").exists())
