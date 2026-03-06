import unittest
from pathlib import Path


class CheckerImportCompatibilityTests(unittest.TestCase):
    def test_forms_does_not_import_checker_constant_from_models(self):
        forms_py = Path("problems/forms.py").read_text(encoding="utf-8")
        self.assertNotIn("from .models import Problem, Tag, CHECKER_CUSTOM", forms_py)


if __name__ == "__main__":
    unittest.main()
