from types import SimpleNamespace
from pathlib import Path
from subprocess import CompletedProcess, TimeoutExpired
from unittest.mock import patch

from django.test import SimpleTestCase

from assessment.services.attempt_downloads import (
    ExportValidationError, _cognitive_distribution, _order_is_valid,
    _ordered_statements, _tf_answer_map,
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

    def test_missing_pdf_renderer_is_a_hard_failure(self):
        from assessment.services.attempt_downloads import _render_pdf

        with patch("assessment.services.attempt_downloads.shutil.which", return_value=None):
            with self.assertRaisesMessage(ExportValidationError, "MISSING_PDF_RENDERER"):
                _render_pdf(b"PK", "document.docx")

    def test_pdf_renderer_uses_an_isolated_writable_profile(self):
        from assessment.services.attempt_downloads import _render_pdf

        def completed(command, **kwargs):
            source = Path(command[-1])
            source.with_suffix(".pdf").write_bytes(b"%PDF-rendered")
            self.assertTrue(any(arg.startswith("-env:UserInstallation=file://") for arg in command))
            self.assertNotEqual(kwargs["env"]["HOME"], "/var/www")
            self.assertEqual(kwargs["env"]["SAL_USE_VCLPLUGIN"], "svp")
            self.assertNotIn("DISPLAY", kwargs["env"])
            self.assertNotIn("WAYLAND_DISPLAY", kwargs["env"])
            self.assertEqual(kwargs["cwd"], str(source.parent))
            return CompletedProcess(command, 0, "", "")

        with patch.dict("assessment.services.attempt_downloads.os.environ", {
                "DISPLAY": ":99", "WAYLAND_DISPLAY": "wayland-0",
        }), patch("assessment.services.attempt_downloads.shutil.which", return_value="/usr/bin/soffice"), \
                patch("assessment.services.attempt_downloads.subprocess.run", side_effect=completed):
            self.assertEqual(_render_pdf(b"PK", "document.docx"), b"%PDF-rendered")

    def test_pdf_renderer_timeout_has_a_stable_error_code(self):
        from assessment.services.attempt_downloads import _render_pdf

        with patch("assessment.services.attempt_downloads.shutil.which", return_value="/usr/bin/soffice"), \
                patch("assessment.services.attempt_downloads.subprocess.run", side_effect=TimeoutExpired("soffice", 120)):
            with self.assertRaisesMessage(ExportValidationError, "PDF_RENDER_TIMEOUT"):
                _render_pdf(b"PK", "document.docx")
