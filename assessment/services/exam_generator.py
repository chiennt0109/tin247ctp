import hashlib
import json
import random

from django.db import transaction

from assessment.models import (
    AssessmentAuditLog, GeneratedExam, GeneratedExamAsset, GeneratedExamQuestion,
)
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.blueprint_feasibility import solve_slot_assignment
from assessment.services.protected_payload import encrypt_json


class ExamGenerationError(ValueError):
    pass


class ExamGenerator:
    @transaction.atomic
    def generate_for_attempt(
        self, session, *, code, seed, actor=None, blueprint_version=None, scoring_version=None,
    ):
        blueprint_version = blueprint_version or session.blueprint_version
        scoring_version = scoring_version or session.scoring_version
        if not blueprint_version.is_locked or not scoring_version.is_locked:
            raise ExamGenerationError("Blueprint and scoring versions must be locked before generation")

        rng = random.Random(str(seed))
        sections = blueprint_version.sections.prefetch_related(
            "slots__curriculum", "slots__outcome"
        ).all()
        slots = [slot for section in sections for slot in section.slots.all()]
        selected = solve_slot_assignment(slots, BlueprintValidator.candidates_for_slot, seed=seed)
        if selected is None:
            shortages = [
                f"slot {slot.pk}: cần {slot.quantity}, pool {len(BlueprintValidator.candidates_for_slot(slot))}"
                for slot in slots
            ]
            raise ExamGenerationError("Không có nghiệm toàn cục; " + "; ".join(shortages))

        if session.shuffle_questions:
            rng.shuffle(selected)
        snapshot_payload = []
        prepared = []
        for order, (slot, question) in enumerate(selected, 1):
            revision = question.current_revision
            options = list(revision.options)
            option_order = list(range(len(options)))
            if session.shuffle_options and question.shuffle_allowed:
                rng.shuffle(option_order)
            ordered_options = [options[index] for index in option_order]
            statement_order = list(range(len(revision.statements)))
            if (session.shuffle_options and question.shuffle_allowed
                    and question.question_type != "TRUE_FALSE_GROUP"):
                rng.shuffle(statement_order)
            ordered_statements = [revision.statements[index] for index in statement_order]
            item = {
                "order": order, "question_id": question.source_question_id,
                "source_version": revision.source_version, "content_hash": revision.content_hash,
                "slot_id": slot.pk, "option_order": option_order,
                "statement_order": statement_order,
                "score": str(slot.score_per_item),
            }
            snapshot_payload.append(item)
            prepared.append((slot, question, revision, order, ordered_options, option_order,
                             ordered_statements, statement_order))

        exam_hash = hashlib.sha256(json.dumps(
            {"session": str(session.pk), "code": code, "seed": str(seed), "items": snapshot_payload},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        report = {
            "valid": True, "question_count": len(prepared),
            "expected_question_count": blueprint_version.expected_question_count,
            "distinct_questions": len({question.pk for _, question in selected}),
            "distinct_families": len({
                question.duplicate_family_id or f"QUESTION:{question.source_question_id}"
                for _, question in selected
            }),
        }
        if len(prepared) != blueprint_version.expected_question_count:
            raise ExamGenerationError("Generated question total does not match blueprint")
        exam = GeneratedExam.objects.create(
            session=session, code=code, seed=str(seed), blueprint_version=blueprint_version,
            scoring_version=scoring_version,
            total_score=blueprint_version.expected_total_score,
            validation_report=report, exam_hash=exam_hash, generated_by=actor,
        )
        for (slot, question, revision, order, ordered_options, option_order,
             ordered_statements, statement_order) in prepared:
            exam_question = GeneratedExamQuestion.objects.create(
                exam=exam, bank_question=question, bank_revision=revision, blueprint_slot=slot,
                order=order, question_id_snapshot=question.source_question_id,
                source_version_snapshot=revision.source_version, stem_snapshot=revision.stem_text,
                options_snapshot=ordered_options, statements_snapshot=ordered_statements,
                protected_answer_snapshot=encrypt_json(revision.protected_answer),
                option_order=option_order, statement_order=statement_order,
                score=slot.score_per_item,
                content_hash_snapshot=revision.content_hash,
            )
            for asset in question.assets.select_related("source_file").all():
                GeneratedExamAsset.objects.create(
                    exam_question=exam_question,
                    source_file_id_snapshot=asset.source_file.source_id,
                    name_snapshot=asset.source_file.name,
                    mime_type_snapshot=asset.source_file.mime_type,
                    source_page_snapshot=asset.source_page,
                    checksum_snapshot=asset.source_file.checksum,
                )
        AssessmentAuditLog.objects.create(
            action="GENERATE_EXAM", actor=actor, object_type="GeneratedExam",
            object_id=str(exam.pk), details={"code": code, "seed": str(seed), "exam_hash": exam_hash},
        )
        return exam
