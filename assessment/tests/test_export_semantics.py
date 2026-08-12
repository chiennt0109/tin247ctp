from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase

from assessment.services.attempt_downloads import (
    ExportValidationError, _cognitive_distribution, _order_is_valid,
    _ordered_statements, _require_golden_templates, _tf_answer_map,
)
from assessment.services.protected_payload import encrypt_json


class ExportSemanticTests(SimpleTestCase):
    def test_tf_statement_levels_and_statement_order_are_independent_of_options(self):
        statements = [
            {"label": "a", "cognitive_level": "HIEU"},
            {"label": "b", "cognitive_level": "HIEU"},
            {"label": "c", "cognitive_level": "BIET"},
            {"label": "d", "cognitive_level": "HIEU"},
        ]
        question = SimpleNamespace(
            statements_snapshot=statements, options_snapshot=[],
            statement_order=[0, 1, 2, 3], option_order=[3, 2, 1, 0],
            protected_answer_snapshot=encrypt_json({"answer_key": [True, False, True, False]}),
            blueprint_slot=SimpleNamespace(cognitive_level="HIEU"),
            bank_question=SimpleNamespace(cognitive_level="HIEU"),
        )

        self.assertEqual(_ordered_statements(question), statements)
        self.assertEqual(
            _cognitive_distribution([question]),
            {"BIET": 1, "HIEU": 3, "VANDUNG": 0},
        )
        self.assertEqual(_tf_answer_map(question), {"a": "Đ", "b": "S", "c": "Đ", "d": "S"})
        self.assertTrue(_order_is_valid(question))

    def test_missing_golden_templates_is_a_hard_failure(self):
        with patch("assessment.services.attempt_downloads.Path.is_file", return_value=False):
            with self.assertRaisesMessage(ExportValidationError, "MISSING_GOLDEN_EXPORT_TEMPLATE"):
                _require_golden_templates()
