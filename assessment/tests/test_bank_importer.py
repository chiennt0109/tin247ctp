import tempfile
from pathlib import Path
from unittest.mock import patch

from django.test import SimpleTestCase
from openpyxl import Workbook, load_workbook

from assessment.services.bank_importer import BankValidationError, WorkbookBankImporter


REQUIRED_HEADERS = {
    "FILES": [
        "FILE_ID", "FILE_NAME", "MIME_TYPE", "DRIVE_URL", "FOLDER_PATH",
        "SOURCE_GROUP", "NOTE", "CHECKSUM", "FILE_STATUS",
    ],
    "CURRICULUM": ["CURRICULUM_ID", "GRADE", "SUBJECT", "PROGRAM_VERSION", "TOPIC_CODE", "TOPIC_NAME", "ORDER_NO", "STATUS", "NOTE"],
    "CURRICULUM_OUTCOMES": ["OUTCOME_ID", "CURRICULUM_ID", "OUTCOME_CODE", "OUTCOME_TEXT", "LEVEL", "STATUS", "NOTE"],
    "QUESTIONS": ["QUESTION_ID", "QUESTION_CODE", "QUESTION_TYPE", "COGNITIVE_LEVEL", "STEM_TEXT", "ANSWER_KEY", "EXPLANATION_ID", "STATUS", "VERSION", "LANGUAGE", "CREATED_AT", "UPDATED_AT", "NOTE", "DIFFICULTY", "COMPETENCY", "ESTIMATED_TIME_SEC", "USE_PURPOSE", "SHUFFLE_ALLOWED", "FAMILY_ID", "PROCESS_STATUS", "CLASSIFICATION_BASIS"],
    "OPTIONS": ["OPTION_ID", "QUESTION_ID", "OPTION_LABEL", "OPTION_TEXT", "IS_CORRECT", "ORDER_NO", "STATUS"],
    "STATEMENTS": ["STATEMENT_ID", "QUESTION_ID", "STATEMENT_LABEL", "STATEMENT_TEXT", "TRUTH_VALUE", "ORDER_NO", "STATUS", "COGNITIVE_LEVEL", "DIFFICULTY", "CLASSIFICATION_BASIS"],
    "QUESTION_CURRICULUM": ["QUESTION_CURRICULUM_ID", "QUESTION_ID", "CURRICULUM_ID", "OUTCOME_ID", "WEIGHT", "STATUS", "NOTE"],
    "QUESTION_SOURCES": ["QUESTION_SOURCE_ID", "QUESTION_ID", "FILE_ID", "SOURCE_PAGE", "SOURCE_SECTION", "SOURCE_REF", "LICENSE_NOTE", "STATUS"],
    "DUPLICATES": ["DUPLICATE_ID"], "POLICY_PROFILES": ["POLICY_PROFILE_ID"],
    "SCORE_RULES": ["SCORE_RULE_ID"], "BLUEPRINTS": ["BLUEPRINT_ID"],
    "BLUEPRINT_CELLS": ["BLUEPRINT_CELL_ID"], "BLUEPRINT_SLOTS": ["BLUEPRINT_SLOT_ID"],
    "QUY_UOC": ["CONFIG_KEY"],
}


class WorkbookFactory:
    @staticmethod
    def create(
        *, missing_answer=False, duplicate_question=False, duplicate_source=False,
        estimated_time=60, reorder_question_headers=False, source_group="", file_note="",
        checksum="",
    ):
        workbook = Workbook()
        workbook.remove(workbook.active)
        for name, headers in REQUIRED_HEADERS.items():
            sheet = workbook.create_sheet(name)
            actual_headers = list(headers)
            if name == "QUESTIONS" and reorder_question_headers:
                estimated_index = actual_headers.index("ESTIMATED_TIME_SEC")
                purpose_index = actual_headers.index("USE_PURPOSE")
                actual_headers[estimated_index], actual_headers[purpose_index] = (
                    actual_headers[purpose_index], actual_headers[estimated_index]
                )
            sheet.append(actual_headers)
        workbook["FILES"].append([
            "F1", "source.pdf", "application/pdf", "https://example.com/f", "/source",
            source_group, file_note, checksum, "PARSED",
        ])
        workbook["CURRICULUM"].append(["C1", 12, "Tin học", "GDPT2018", "A", "Topic", 1, "REVIEW", ""])
        workbook["CURRICULUM_OUTCOMES"].append(["O1", "C1", "YCCD_01", "Outcome", "BIET", "REVIEW", ""])
        question = dict(zip(REQUIRED_HEADERS["QUESTIONS"], [
            "Q1", "Q1", "MCQ_SINGLE", "BIET", "Stem", None if missing_answer else "A",
            "", "ACTIVE", 1, "vi", "", "", "", 1, "NLa", estimated_time, "PRACTICE",
            True, "FAM1", "READY_FOR_PRACTICE", "YCCD",
        ]))
        question_headers = [cell.value for cell in workbook["QUESTIONS"][1]]
        question_row = [question[header] for header in question_headers]
        workbook["QUESTIONS"].append(question_row)
        if duplicate_question:
            workbook["QUESTIONS"].append(question_row)
        for index, label in enumerate("ABCD", 1):
            workbook["OPTIONS"].append([f"OP{index}", "Q1", label, label, label == "A", index, "APPROVED"])
        workbook["QUESTION_CURRICULUM"].append(["QC1", "Q1", "C1", "O1", 1, "APPROVED", ""])
        workbook["QUESTION_SOURCES"].append(["QS1", "Q1", "F1", "1", "", "", "", "APPROVED"])
        if duplicate_source:
            workbook["QUESTION_SOURCES"].append(
                ["QS2", "Q1", "F1", "2", "updated-section", "updated-ref", "updated-license", "APPROVED"]
            )
        handle = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
        handle.close()
        workbook.save(handle.name)
        return Path(handle.name)


class WorkbookBankImporterTests(SimpleTestCase):
    def test_parses_valid_question_and_stable_hash(self):
        path = WorkbookFactory.create()
        self.addCleanup(path.unlink)
        first = WorkbookBankImporter().parse(path)
        second = WorkbookBankImporter().parse(path)
        self.assertFalse(first.errors)
        self.assertEqual(first.questions[0]["content_hash"], second.questions[0]["content_hash"])

    def test_rejects_missing_answer(self):
        path = WorkbookFactory.create(missing_answer=True)
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertIn("MISSING_ANSWER", parsed.errors[0]["issues"])

    def test_rejects_duplicate_question_key(self):
        path = WorkbookFactory.create(duplicate_question=True)
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertTrue(any(error["code"] == "DUPLICATE_KEY" for error in parsed.errors))

    def test_single_outcome_physical_row_is_not_a_duplicate(self):
        path = WorkbookFactory.create()
        self.addCleanup(path.unlink)

        parsed = WorkbookBankImporter().parse(path)

        self.assertEqual(parsed.key_rows["CURRICULUM_OUTCOMES"]["O1"], [2])
        self.assertFalse(any(
            error["code"] == "DUPLICATE_KEY" and error["sheet"] == "CURRICULUM_OUTCOMES"
            for error in parsed.errors
        ))

    def test_duplicate_outcome_reports_distinct_physical_rows_and_values(self):
        path = WorkbookFactory.create()
        workbook = load_workbook(path)
        workbook["CURRICULUM_OUTCOMES"].append(
            ["Ｏ1 ", "C1", "YCCD_02", "Duplicate", "BIET", "REVIEW", ""],
        )
        workbook.save(path)
        self.addCleanup(path.unlink)

        parsed = WorkbookBankImporter().parse(path)
        error = next(
            error for error in parsed.errors
            if error["code"] == "DUPLICATE_KEY" and error["sheet"] == "CURRICULUM_OUTCOMES"
        )

        self.assertEqual(error["key"], "O1")
        self.assertEqual(error["count"], 2)
        self.assertEqual(error["row_numbers"], [2, 3])
        self.assertEqual(error["raw_values"], ["O1", "Ｏ1 "])
        self.assertEqual(error["normalized_values"], ["O1", "O1"])

    def test_same_physical_outcome_row_appended_twice_is_not_duplicate(self):
        records = [{
            "OUTCOME_ID": "O1", "__row__": 133,
            "__key_raw__": "O1", "__key_normalized__": "O1",
        }]
        errors = []

        indexes = WorkbookBankImporter._validate_unique_keys(
            {"CURRICULUM_OUTCOMES": records + records}, errors,
        )

        self.assertEqual(indexes["CURRICULUM_OUTCOMES"]["O1"], [133])
        self.assertEqual(errors, [])

    def test_question_and_blueprint_references_do_not_duplicate_outcome(self):
        path = WorkbookFactory.create()
        workbook = load_workbook(path)
        sheet = workbook["BLUEPRINT_CELLS"]
        sheet.cell(row=1, column=2, value="OUTCOME_ID")
        sheet.append(["BC1", "O1"])
        workbook.save(path)
        self.addCleanup(path.unlink)

        parsed = WorkbookBankImporter().parse(path)

        self.assertEqual(parsed.key_rows["CURRICULUM_OUTCOMES"]["O1"], [2])
        self.assertFalse(any(
            error["code"] == "DUPLICATE_KEY" and error.get("key") == "O1"
            for error in parsed.errors
        ))

    def test_curriculum_outcomes_worksheet_is_parsed_once(self):
        path = WorkbookFactory.create()
        self.addCleanup(path.unlink)
        from assessment.services import bank_importer

        with patch.object(bank_importer, "_sheet_rows", wraps=bank_importer._sheet_rows) as reader:
            WorkbookBankImporter().parse(path)

        outcome_calls = [call for call in reader.call_args_list if call.args[1] == "CURRICULUM_OUTCOMES"]
        self.assertEqual(len(outcome_calls), 1)

    def test_rejects_missing_required_sheet(self):
        path = WorkbookFactory.create()
        workbook = load_workbook(path)
        del workbook["QUESTIONS"]
        workbook.save(path)
        self.addCleanup(path.unlink)
        with self.assertRaises(BankValidationError):
            WorkbookBankImporter().parse(path)

    def test_deduplicates_question_sources_by_question_and_file(self):
        path = WorkbookFactory.create(duplicate_source=True)
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertFalse(parsed.errors)
        self.assertEqual(len(parsed.questions[0]["sources"]), 1)
        self.assertEqual(parsed.questions[0]["sources"][0]["SOURCE_PAGE"], "2")

    def test_estimated_time_accepts_integer(self):
        path = WorkbookFactory.create(estimated_time=75)
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertFalse(parsed.errors)
        self.assertEqual(parsed.questions[0]["estimated_time_seconds"], 75)

    def test_dry_run_reports_remaining_char_field_overflow(self):
        path = WorkbookFactory.create(checksum="x" * 129)
        self.addCleanup(path.unlink)

        parsed = WorkbookBankImporter().parse(path)

        self.assertIn({
            "code": "FIELD_TOO_LONG", "sheet": "FILES", "row": 2,
            "column": "CHECKSUM", "field": "checksum", "length": 129,
            "max_length": 128,
        }, parsed.errors)

    def test_estimated_time_blank_becomes_none(self):
        path = WorkbookFactory.create(estimated_time="")
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertFalse(parsed.errors)
        self.assertIsNone(parsed.questions[0]["estimated_time_seconds"])

    def test_estimated_time_accepts_numeric_string(self):
        path = WorkbookFactory.create(estimated_time="90")
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertFalse(parsed.errors)
        self.assertEqual(parsed.questions[0]["estimated_time_seconds"], 90)

    def test_estimated_time_rejects_purpose_value_during_dry_run(self):
        path = WorkbookFactory.create(estimated_time="PRACTICE")
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertTrue(parsed.has_fatal_errors)
        self.assertTrue(any(
            error.get("code") == "INVALID_FIELD_TYPE"
            and error.get("field") == "ESTIMATED_TIME_SEC"
            and error.get("value") == "PRACTICE"
            for error in parsed.errors
        ))

    def test_question_columns_are_mapped_by_normalized_header(self):
        path = WorkbookFactory.create(estimated_time="120", reorder_question_headers=True)
        self.addCleanup(path.unlink)
        parsed = WorkbookBankImporter().parse(path)
        self.assertFalse(parsed.errors)
        self.assertEqual(parsed.questions[0]["estimated_time_seconds"], 120)
        self.assertEqual(parsed.questions[0]["use_purpose"], "PRACTICE")
