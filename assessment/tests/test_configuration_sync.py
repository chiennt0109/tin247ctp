from types import SimpleNamespace

from django.test import TestCase

from assessment.models import ExamBlueprint, ExamBlueprintGroup
from assessment.services.configuration_sync import MasterConfigurationSync


class MasterConfigurationSyncTests(TestCase):
    def test_pool_report_distinguishes_candidate_margin_from_filled_cells(self):
        parsed = SimpleNamespace(
            rows={
                "BLUEPRINTS": [{
                    "BLUEPRINT_ID": "BP10", "BLUEPRINT_NAME": "K10", "EXAM_TYPE": "PERIODIC",
                    "GRADE": 10, "STATUS": "APPROVED",
                }],
                "BLUEPRINT_CELLS": [{
                    "BLUEPRINT_CELL_ID": cell_id, "BLUEPRINT_ID": "BP10", "QUESTION_TYPE": "ESSAY",
                    "REQUIRED_COUNT": 1, "STATUS": "APPROVED", "CURRICULUM_ID": curriculum,
                    "OUTCOME_ID": "", "COGNITIVE_LEVEL": "", "DIFFICULTY": None, "COMPETENCY": "",
                } for cell_id, curriculum in (("E1", "C1"), ("E2", "C2"), ("E3", "C3"))],
            },
            questions=[{
                "question_id": question_id, "question_type": "ESSAY",
                "process_status": "READY_FOR_PERIODIC", "curriculum_id": curriculum,
                "outcome_id": "", "cognitive_level": "BIET", "difficulty": 1,
                "competency": "NLa", "family_id": question_id, "row": {"STATUS": "ACTIVE"},
            } for question_id, curriculum in (("Q1", "C1"), ("Q2", "C1"), ("Q3", "C2"))],
        )
        parsed.rows["QUESTION_CURRICULUM"] = [{
            "QUESTION_ID": question_id, "CURRICULUM_ID": curriculum,
            "OUTCOME_ID": "", "STATUS": "APPROVED",
        } for question_id, curriculum in (("Q1", "C1"), ("Q2", "C1"), ("Q3", "C2"))]

        report = MasterConfigurationSync().preview(parsed)["blueprint_pool"][0]

        self.assertEqual(report["required"], {"ESSAY": 3})
        self.assertEqual(report["eligible"], {"ESSAY": 2})
        self.assertEqual(report["eligible_capacity"], {"ESSAY": 3})
        self.assertEqual(report["missing_count"], 1)
        self.assertFalse(report["can_generate"])

    def test_grade_12_practice_blueprint_uses_practice_topic_pool(self):
        blueprint_ids = (
            "BP_G12_PRACTICE_AI_IOAI_2026_CS_50Q_V1",
            "BP_G12_PRACTICE_AI_IOAI_2026_CS_V1",
        )
        parsed = SimpleNamespace(
            rows={
                "BLUEPRINTS": [{
                    "BLUEPRINT_ID": blueprint_id, "BLUEPRINT_NAME": "IOAI practice",
                    "EXAM_TYPE": "PRACTICE", "GRADE": 12, "STATUS": "APPROVED",
                } for blueprint_id in blueprint_ids],
                "BLUEPRINT_CELLS": [{
                    "BLUEPRINT_CELL_ID": f"PRACTICE-CELL-{index}",
                    "BLUEPRINT_ID": blueprint_id,
                    "QUESTION_TYPE": "MCQ_SINGLE", "REQUIRED_COUNT": 1,
                    "STATUS": "APPROVED", "CURRICULUM_ID": "C1", "OUTCOME_ID": "",
                    "COGNITIVE_LEVEL": "BIET", "DIFFICULTY": 1, "COMPETENCY": "NLa",
                } for index, blueprint_id in enumerate(blueprint_ids, 1)],
                "QUESTION_CURRICULUM": [{
                    "QUESTION_ID": "Q1", "CURRICULUM_ID": "C1", "OUTCOME_ID": "",
                    "STATUS": "APPROVED",
                }],
            },
            questions=[{
                "question_id": "Q1", "question_type": "MCQ_SINGLE",
                "process_status": "READY_FOR_PRACTICE", "cognitive_level": "BIET",
                "difficulty": 1, "competency": "NLa", "family_id": "Q1",
                "row": {"STATUS": "ACTIVE"},
            }],
        )

        preview = MasterConfigurationSync().preview(parsed)

        self.assertEqual(preview["approved_blueprints"], 2)
        self.assertEqual(preview["grades"], [12])
        self.assertEqual(
            {report["blueprint"] for report in preview["blueprint_pool"]}, set(blueprint_ids),
        )
        self.assertTrue(all(report["can_generate"] for report in preview["blueprint_pool"]))

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
            "BLUEPRINT_SLOTS": [{
                "BLUEPRINT_SLOT_ID": f"SLOT-{grade}", "BLUEPRINT_ID": f"TX-{grade}",
                "SLOT_NO": 1, "BLUEPRINT_CELL_ID": f"CELL-{grade}",
                "QUESTION_ID": "", "STATUS": "APPROVED", "NOTE": "",
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
