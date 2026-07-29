import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook


QUESTION_TYPES = {"MCQ_SINGLE", "TRUE_FALSE_GROUP", "SHORT_ANSWER", "ESSAY", "PRACTICAL"}
COGNITIVE_LEVELS = {"BIET", "HIEU", "VANDUNG"}
PROCESS_STATUSES = {
    "RAW", "NORMALIZED", "CURRICULUM_MAPPED", "CLASSIFIED", "DUPLICATE_CHECKED",
    "ANSWER_CHECKED", "CONTENT_REVIEWED", "READY_FOR_PRACTICE", "READY_FOR_PERIODIC",
    "READY_FOR_GRADUATION", "NEEDS_REVIEW", "OUTDATED", "RETIRED",
}
REQUIRED_SHEETS = {
    "FILES", "CURRICULUM", "CURRICULUM_OUTCOMES", "QUESTIONS", "OPTIONS", "STATEMENTS",
    "QUESTION_CURRICULUM", "QUESTION_SOURCES", "DUPLICATES", "POLICY_PROFILES",
    "SCORE_RULES", "BLUEPRINTS", "BLUEPRINT_CELLS", "BLUEPRINT_SLOTS", "QUY_UOC",
}


class BankValidationError(ValueError):
    pass


def _canonical(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


def _boolean(value):
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().upper()
    if normalized in {"TRUE", "1", "YES"}:
        return True
    if normalized in {"FALSE", "0", "NO"}:
        return False
    raise BankValidationError(f"Invalid boolean value: {value!r}")


def _sheet_rows(workbook, name):
    sheet = workbook[name]
    iterator = sheet.iter_rows(values_only=True)
    headers = [str(value).strip() if value is not None else "" for value in next(iterator)]
    rows = []
    for row_number, values in enumerate(iterator, start=2):
        record = {header: _canonical(value) for header, value in zip(headers, values) if header}
        # Master rule: the first column is the unique key. Formatting/formula-only rows are ignored.
        if not record.get(headers[0]):
            continue
        record["__row__"] = row_number
        rows.append(record)
    return rows


@dataclass
class ParsedBank:
    source_path: str
    source_sha256: str
    rows: dict
    questions: list
    errors: list
    warnings: list

    @property
    def has_fatal_errors(self):
        return bool(self.errors)


class WorkbookBankImporter:
    def parse(self, source_path):
        source_path = str(Path(source_path))
        payload = Path(source_path).read_bytes()
        raw = load_workbook(source_path, read_only=True, data_only=False)
        cached = load_workbook(source_path, read_only=True, data_only=True)
        missing = sorted(REQUIRED_SHEETS - set(cached.sheetnames))
        if missing:
            raise BankValidationError(f"Missing required sheets: {', '.join(missing)}")

        rows = {name: _sheet_rows(cached, name) for name in cached.sheetnames}
        raw_rows = {name: _sheet_rows(raw, name) for name in ("QUESTIONS",)}
        errors, warnings = [], []
        self._validate_unique_keys(rows, errors)
        questions = self._build_questions(rows, raw_rows, errors, warnings)
        return ParsedBank(
            source_path=source_path,
            source_sha256=hashlib.sha256(payload).hexdigest(),
            rows=rows,
            questions=questions,
            errors=errors,
            warnings=warnings,
        )

    @staticmethod
    def _validate_unique_keys(rows, errors):
        for sheet, records in rows.items():
            if not records:
                continue
            key = next(field for field in records[0] if field != "__row__")
            counts = Counter(str(record.get(key)) for record in records)
            for value, count in counts.items():
                if count > 1:
                    errors.append({"code": "DUPLICATE_KEY", "sheet": sheet, "key": value, "count": count})

    def _build_questions(self, rows, raw_rows, errors, warnings):
        curriculum_ids = {str(row.get("CURRICULUM_ID")) for row in rows["CURRICULUM"]}
        outcomes = {str(row.get("OUTCOME_ID")): str(row.get("CURRICULUM_ID")) for row in rows["CURRICULUM_OUTCOMES"]}
        file_ids = {str(row.get("FILE_ID")) for row in rows["FILES"]}
        options = defaultdict(list)
        for row in rows["OPTIONS"]:
            options[str(row.get("QUESTION_ID"))].append(row)
        statements = defaultdict(list)
        for row in rows["STATEMENTS"]:
            statements[str(row.get("QUESTION_ID"))].append(row)
        mappings = {str(row.get("QUESTION_ID")): row for row in rows["QUESTION_CURRICULUM"]}
        sources = defaultdict(list)
        for row in rows["QUESTION_SOURCES"]:
            sources[str(row.get("QUESTION_ID"))].append(row)
        # QUESTION_SOURCES has its own row key, but the operational relation is
        # unique per (question, source file). Normalize duplicate source rows
        # before handing them to the persistence service. The last row wins so
        # corrected metadata from a later master row is applied deterministically.
        for question_id, question_sources in tuple(sources.items()):
            deduplicated = {}
            for source in question_sources:
                deduplicated[str(source.get("FILE_ID"))] = source
            sources[question_id] = list(deduplicated.values())
        raw_by_id = {str(row.get("QUESTION_ID")): row for row in raw_rows["QUESTIONS"]}
        result = []
        for row in rows["QUESTIONS"]:
            qid = str(row.get("QUESTION_ID"))
            qerrors = []
            qtype = str(row.get("QUESTION_TYPE") or "")
            if qtype not in QUESTION_TYPES:
                qerrors.append("INVALID_QUESTION_TYPE")
            if str(row.get("COGNITIVE_LEVEL") or "") not in COGNITIVE_LEVELS:
                qerrors.append("INVALID_COGNITIVE_LEVEL")
            if not str(row.get("STEM_TEXT") or "").strip():
                qerrors.append("MISSING_STEM")
            if row.get("ANSWER_KEY") in (None, ""):
                qerrors.append("MISSING_ANSWER")
            if str(row.get("PROCESS_STATUS") or "") not in PROCESS_STATUSES:
                qerrors.append("INVALID_PROCESS_STATUS")
            try:
                difficulty = int(row.get("DIFFICULTY"))
                if difficulty not in range(1, 6):
                    raise ValueError
            except (TypeError, ValueError):
                qerrors.append("INVALID_DIFFICULTY")
                difficulty = None
            try:
                shuffle_allowed = _boolean(row.get("SHUFFLE_ALLOWED"))
            except BankValidationError:
                qerrors.append("INVALID_SHUFFLE_ALLOWED")
                shuffle_allowed = False
            if qtype == "MCQ_SINGLE":
                qoptions = options[qid]
                if len(qoptions) != 4 or sum(_boolean(item.get("IS_CORRECT")) for item in qoptions) != 1:
                    qerrors.append("INVALID_OPTIONS")
            if qtype == "TRUE_FALSE_GROUP" and len(statements[qid]) != 4:
                qerrors.append("INVALID_STATEMENTS")
            if qid not in mappings:
                qerrors.append("MISSING_CURRICULUM_LINK")
            else:
                mapping = mappings[qid]
                curriculum_id = str(mapping.get("CURRICULUM_ID"))
                outcome_id = str(mapping.get("OUTCOME_ID"))
                if curriculum_id not in curriculum_ids:
                    qerrors.append("UNKNOWN_CURRICULUM")
                if outcome_id not in outcomes or outcomes.get(outcome_id) != curriculum_id:
                    qerrors.append("INVALID_OUTCOME_LINK")
            if not sources[qid]:
                qerrors.append("MISSING_SOURCE")
            elif any(str(source.get("FILE_ID")) not in file_ids for source in sources[qid]):
                qerrors.append("MISSING_ASSET")
            raw_row = raw_by_id.get(qid, {})
            formula_fields = {}
            for field in ("DIFFICULTY", "COMPETENCY", "USE_PURPOSE", "SHUFFLE_ALLOWED",
                          "FAMILY_ID", "PROCESS_STATUS", "CLASSIFICATION_BASIS"):
                raw_value = raw_row.get(field)
                if isinstance(raw_value, str) and raw_value.startswith("="):
                    formula_fields[field] = raw_value
                    if row.get(field) is None:
                        qerrors.append(f"MISSING_CACHED_{field}")
            if qerrors:
                errors.append({"code": "INVALID_QUESTION", "question_id": qid, "issues": qerrors})
                continue
            normalized_options = [
                {"label": item.get("OPTION_LABEL"), "text": item.get("OPTION_TEXT"),
                 "is_correct": _boolean(item.get("IS_CORRECT")), "order": int(item.get("ORDER_NO"))}
                for item in sorted(options[qid], key=lambda item: int(item.get("ORDER_NO") or 0))
            ]
            normalized_statements = [
                {"label": item.get("STATEMENT_LABEL"), "text": item.get("STATEMENT_TEXT"),
                 "truth_value": _boolean(item.get("TRUTH_VALUE")), "order": int(item.get("ORDER_NO")),
                 "cognitive_level": item.get("COGNITIVE_LEVEL"), "difficulty": item.get("DIFFICULTY")}
                for item in sorted(statements[qid], key=lambda item: int(item.get("ORDER_NO") or 0))
            ]
            mapping = mappings[qid]
            canonical = {
                "question_id": qid, "question_code": row.get("QUESTION_CODE"), "question_type": qtype,
                "cognitive_level": row.get("COGNITIVE_LEVEL"), "stem_text": row.get("STEM_TEXT"),
                "answer_key": row.get("ANSWER_KEY"), "source_version": str(row.get("VERSION")),
                "options": normalized_options, "statements": normalized_statements,
                "curriculum_id": mapping.get("CURRICULUM_ID"), "outcome_id": mapping.get("OUTCOME_ID"),
                "difficulty": difficulty, "competency": row.get("COMPETENCY"),
                "process_status": row.get("PROCESS_STATUS"), "use_purpose": row.get("USE_PURPOSE"),
                "shuffle_allowed": shuffle_allowed, "family_id": row.get("FAMILY_ID"),
            }
            content_hash = hashlib.sha256(
                json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            canonical.update({
                "content_hash": content_hash, "row": row, "mapping": mapping,
                "sources": sources[qid], "formula_fields": formula_fields,
            })
            result.append(canonical)
        return result
