from collections import defaultdict
from decimal import Decimal
import json

from django.db import transaction
from django.utils.text import slugify

from assessment.models import (
    BlueprintSection, BlueprintSlot, BlueprintVersion, CurriculumNode, CurriculumOutcome,
    ExamBlueprint, ExamBlueprintGroup, ScoringRule, ScoringScheme, ScoringSchemeVersion,
)


TYPE_MAP = {
    "TN_4_LUA_CHON": "MCQ_SINGLE", "MCQ": "MCQ_SINGLE",
    "DUNG_SAI": "TRUE_FALSE_GROUP", "TRA_LOI_NGAN": "SHORT_ANSWER",
}
PROCESS_STATUS_MAP = {
    "REGULAR": "READY_FOR_PERIODIC", "THUONG_XUYEN": "READY_FOR_PERIODIC",
    "PERIODIC": "READY_FOR_PERIODIC", "GRADUATION": "READY_FOR_GRADUATION",
}


def _json_safe(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


class ConfigurationSyncError(ValueError):
    pass


class MasterConfigurationSync:
    def preview(self, parsed):
        approved = [row for row in parsed.rows.get("BLUEPRINTS", []) if str(row.get("STATUS")) == "APPROVED"]
        pool_report = self._source_pool_report(parsed, approved)
        return {
            "approved_blueprints": len(approved),
            "grades": sorted({int(row["GRADE"]) for row in approved if row.get("GRADE")}),
            "regular_blueprints": sum(str(row.get("EXAM_TYPE")) in {"REGULAR", "THUONG_XUYEN"} for row in approved),
            "blueprint_cells": sum(
                str(row.get("STATUS")) == "APPROVED" for row in parsed.rows.get("BLUEPRINT_CELLS", [])
            ),
            "blueprint_pool": pool_report,
        }

    @staticmethod
    def _source_pool_report(parsed, blueprints):
        """Evaluate source questions against source cells without writing the database."""
        cells_by_blueprint = defaultdict(list)
        for cell in parsed.rows.get("BLUEPRINT_CELLS", []):
            if str(cell.get("STATUS")) == "APPROVED":
                cells_by_blueprint[str(cell.get("BLUEPRINT_ID"))].append(cell)
        reports = []
        for blueprint in blueprints:
            if int(blueprint.get("GRADE") or 0) != 10:
                continue
            exam_type = str(blueprint.get("EXAM_TYPE") or "")
            required_status = PROCESS_STATUS_MAP.get(exam_type, "")
            used_ids, used_families = set(), set()
            required_by_type, eligible_by_type = defaultdict(int), defaultdict(int)
            missing = []
            for cell in cells_by_blueprint[str(blueprint.get("BLUEPRINT_ID"))]:
                qtype = TYPE_MAP.get(str(cell.get("QUESTION_TYPE")), str(cell.get("QUESTION_TYPE")))
                required = int(cell.get("REQUIRED_COUNT") or 0)
                candidates = []
                for question in getattr(parsed, "questions", ()):
                    family = question.get("family_id") or f"QUESTION:{question['question_id']}"
                    if question["question_id"] in used_ids or family in used_families:
                        continue
                    filters = (
                        question["question_type"] == qtype
                        and (not required_status or question["process_status"] == required_status)
                        and (not cell.get("CURRICULUM_ID") or str(question["curriculum_id"]) == str(cell["CURRICULUM_ID"]))
                        and (not cell.get("OUTCOME_ID") or str(question["outcome_id"]) == str(cell["OUTCOME_ID"]))
                        and (not cell.get("COGNITIVE_LEVEL") or question["cognitive_level"] == str(cell["COGNITIVE_LEVEL"]))
                        and (not cell.get("DIFFICULTY") or question["difficulty"] == int(cell["DIFFICULTY"]))
                        and (not cell.get("COMPETENCY") or question.get("competency") == str(cell["COMPETENCY"]))
                    )
                    if filters:
                        candidates.append(question)
                distinct = []
                local_families = set()
                for question in candidates:
                    family = question.get("family_id") or f"QUESTION:{question['question_id']}"
                    if family not in local_families:
                        distinct.append(question)
                        local_families.add(family)
                required_by_type[qtype] += required
                eligible_by_type[qtype] += len(distinct)
                selected = distinct[:required]
                used_ids.update(question["question_id"] for question in selected)
                used_families.update(
                    question.get("family_id") or f"QUESTION:{question['question_id']}"
                    for question in selected
                )
                if len(selected) < required:
                    missing.append({
                        "cell_id": str(cell.get("BLUEPRINT_CELL_ID")), "question_type": qtype,
                        "required": required, "eligible": len(distinct), "missing": required - len(selected),
                    })
            reports.append({
                "blueprint": str(blueprint.get("BLUEPRINT_ID")),
                "name": str(blueprint.get("BLUEPRINT_NAME") or ""),
                "required": dict(required_by_type), "eligible": dict(eligible_by_type),
                "missing_slots": missing, "can_generate": not missing,
            })
        return reports

    @transaction.atomic
    def apply(self, parsed, *, actor=None):
        report = self.preview(parsed)
        cells = defaultdict(list)
        for row in parsed.rows.get("BLUEPRINT_CELLS", []):
            if str(row.get("STATUS")) == "APPROVED":
                cells[str(row.get("BLUEPRINT_ID"))].append(row)
        score_rows = [row for row in parsed.rows.get("SCORE_RULES", []) if str(row.get("STATUS")) == "APPROVED"]
        created = updated = 0
        for source in parsed.rows.get("BLUEPRINTS", []):
            if str(source.get("STATUS")) != "APPROVED":
                continue
            source_id = str(source["BLUEPRINT_ID"])
            group = None
            group_code = str(
                source.get("EQUIVALENCE_GROUP")
                or source.get("BLUEPRINT_GROUP")
                or source.get("GROUP_CODE")
                or ""
            ).strip()
            if group_code:
                group, _ = ExamBlueprintGroup.objects.get_or_create(
                    code=slugify(group_code) or group_code,
                    defaults={
                        "name": group_code,
                        "exam_type": str(source.get("EXAM_TYPE") or "GRADUATION"),
                    },
                )
            blueprint, was_created = ExamBlueprint.objects.update_or_create(
                source_blueprint_id=source_id,
                defaults={
                    "name": str(source["BLUEPRINT_NAME"]),
                    "exam_type": str(source["EXAM_TYPE"]), "grade": int(source["GRADE"]),
                    "subject": str(source.get("SUBJECT") or "Tin học"),
                    "semester": str(source.get("SEMESTER") or ""),
                    "total_questions": int(source["TOTAL_QUESTIONS"]),
                    "total_score": Decimal(str(source["TOTAL_SCORE"])),
                    "duration_minutes": int(source["DURATION_MIN"]),
                    "status": ExamBlueprint.Status.APPROVED, "notes": str(source.get("NOTE") or ""),
                    "created_by": actor,
                },
            )
            if group:
                group.blueprints.add(blueprint)
            version_number = int(source.get("VERSION") or 1)
            version, version_created = BlueprintVersion.objects.get_or_create(
                blueprint=blueprint, version=version_number,
                defaults={
                    "duration_minutes": int(source["DURATION_MIN"]),
                    "expected_question_count": int(source["TOTAL_QUESTIONS"]),
                    "expected_total_score": Decimal(str(source["TOTAL_SCORE"])),
                    "source_blueprint_id": source_id, "source_snapshot": _json_safe(source), "created_by": actor,
                },
            )
            if version.is_locked:
                continue
            version.duration_minutes = int(source["DURATION_MIN"])
            version.expected_question_count = int(source["TOTAL_QUESTIONS"])
            version.expected_total_score = Decimal(str(source["TOTAL_SCORE"]))
            version.source_snapshot = _json_safe(source)
            version.save()
            version.sections.all().delete()
            for order, row in enumerate(cells[source_id], 1):
                question_type = TYPE_MAP.get(str(row["QUESTION_TYPE"]), str(row["QUESTION_TYPE"]))
                section, _ = BlueprintSection.objects.get_or_create(
                    version=version, code=question_type,
                    defaults={"name": question_type, "order": order},
                )
                curriculum = CurriculumNode.objects.filter(source_id=str(row.get("CURRICULUM_ID"))).first()
                outcome = CurriculumOutcome.objects.filter(source_id=str(row.get("OUTCOME_ID"))).first()
                BlueprintSlot.objects.create(
                    section=section, order=order, curriculum=curriculum, outcome=outcome,
                    question_type=question_type, cognitive_level=str(row.get("COGNITIVE_LEVEL") or ""),
                    difficulty=int(row["DIFFICULTY"]) if row.get("DIFFICULTY") else None,
                    competency=str(row.get("COMPETENCY") or ""), quantity=int(row["REQUIRED_COUNT"]),
                    score_per_item=Decimal(str(row["SCORE_PER_ITEM"])),
                    required_process_status=PROCESS_STATUS_MAP.get(str(source["EXAM_TYPE"]), ""),
                    requires_graduation_eligibility=str(source["EXAM_TYPE"]) == "GRADUATION",
                )
            policy_id = str(source.get("POLICY_PROFILE_ID") or f"BLUEPRINT:{source_id}")
            scheme, _ = ScoringScheme.objects.get_or_create(
                name=f"{source['BLUEPRINT_NAME']} — Quy tắc chấm",
                defaults={"created_by": actor},
            )
            scoring, _ = ScoringSchemeVersion.objects.get_or_create(
                scheme=scheme, version=version_number,
                defaults={
                    "total_score": Decimal(str(source["TOTAL_SCORE"])),
                    "source_policy_id": policy_id, "source_snapshot": {"blueprint": _json_safe(source)},
                    "created_by": actor,
                },
            )
            if not scoring.is_locked:
                scoring.rules.all().delete()
                for rule_order, rule in enumerate(score_rows, 1):
                    if str(rule.get("POLICY_PROFILE_ID")) != policy_id:
                        continue
                    question_type = TYPE_MAP.get(str(rule["QUESTION_TYPE"]), str(rule["QUESTION_TYPE"]))
                    ScoringRule.objects.create(
                        version=scoring, question_type=question_type,
                        rule_code=str(rule["RULE_CODE"]), max_score=Decimal(str(rule["MAX_SCORE"])),
                        configuration=_json_safe({
                            key.lower(): value for key, value in rule.items() if not key.startswith("__")
                        }),
                        order=rule_order,
                    )
            created += was_created
            updated += not was_created
        return {**report, "created": created, "updated": updated}
