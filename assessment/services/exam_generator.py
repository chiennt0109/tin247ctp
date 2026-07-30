import hashlib
import json
import random

from django.db import transaction

from assessment.models import (
    AssessmentAuditLog, GeneratedExam, GeneratedExamAsset, GeneratedExamQuestion,
)
from assessment.services.blueprint_validator import BlueprintValidator
from assessment.services.protected_payload import encrypt_json


class ExamGenerationError(ValueError):
    pass


class ExamGenerator:
    @transaction.atomic
    def _generate(self, session, *, code, seed, purpose, actor=None, expires_at=None):
        if not session.blueprint_version.is_locked or not session.scoring_version.is_locked:
            raise ExamGenerationError("Blueprint and scoring versions must be locked before generation")
        if purpose not in GeneratedExam.Purpose.values:
            raise ExamGenerationError("Generated exam purpose must be ATTEMPT or PREVIEW")
        if purpose == GeneratedExam.Purpose.PREVIEW and expires_at is None:
            raise ExamGenerationError("A persisted preview must have expires_at")

        rng = random.Random(str(seed))
        selected = []
        used_question_ids, used_family_keys = set(), set()
        sections = session.blueprint_version.sections.prefetch_related(
            "slots__curriculum", "slots__outcome"
        ).all()
        for section in sections:
            for slot in section.slots.all():
                candidates = list(
                    BlueprintValidator._candidate_queryset(slot)
                    .filter(current_revision__isnull=False)
                    .select_related("current_revision")
                    .prefetch_related("assets__source_file")
                    .order_by("source_question_id")
                )
                rng.shuffle(candidates)
                slot_selected = []
                for question in candidates:
                    family_key = question.duplicate_family_id or f"QUESTION:{question.source_question_id}"
                    if question.pk in used_question_ids or family_key in used_family_keys:
                        continue
                    slot_selected.append(question)
                    used_question_ids.add(question.pk)
                    used_family_keys.add(family_key)
                    if len(slot_selected) == slot.quantity:
                        break
                if len(slot_selected) != slot.quantity:
                    raise ExamGenerationError(
                        f"Slot {slot.pk} requires {slot.quantity} questions but only "
                        f"{len(slot_selected)} distinct candidates are selectable"
                    )
                selected.extend((slot, question) for question in slot_selected)

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
            item = {
                "order": order, "question_id": question.source_question_id,
                "source_version": revision.source_version, "content_hash": revision.content_hash,
                "slot_id": slot.pk, "option_order": option_order,
                "score": str(slot.score_per_item),
            }
            snapshot_payload.append(item)
            prepared.append((slot, question, revision, order, ordered_options, option_order))

        exam_hash = hashlib.sha256(json.dumps(
            {"session": str(session.pk), "code": code, "seed": str(seed), "items": snapshot_payload},
            ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        ).encode()).hexdigest()
        report = {
            "valid": True, "question_count": len(prepared),
            "expected_question_count": session.blueprint_version.expected_question_count,
            "distinct_questions": len(used_question_ids), "distinct_families": len(used_family_keys),
        }
        if len(prepared) != session.blueprint_version.expected_question_count:
            raise ExamGenerationError("Generated question total does not match blueprint")
        exam = GeneratedExam.objects.create(
            session=session, code=code, seed=str(seed), blueprint_version=session.blueprint_version,
            scoring_version=session.scoring_version,
            total_score=session.blueprint_version.expected_total_score,
            validation_report=report, exam_hash=exam_hash, generated_by=actor,
            purpose=purpose, expires_at=expires_at,
        )
        for slot, question, revision, order, ordered_options, option_order in prepared:
            exam_question = GeneratedExamQuestion.objects.create(
                exam=exam, bank_question=question, bank_revision=revision, blueprint_slot=slot,
                order=order, question_id_snapshot=question.source_question_id,
                source_version_snapshot=revision.source_version, stem_snapshot=revision.stem_text,
                options_snapshot=ordered_options, statements_snapshot=revision.statements,
                protected_answer_snapshot=encrypt_json(revision.protected_answer),
                option_order=option_order, score=slot.score_per_item,
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

    def generate_preview(self, session, *, code, seed, actor=None, expires_at):
        return self._generate(
            session, code=code, seed=seed, purpose=GeneratedExam.Purpose.PREVIEW,
            actor=actor, expires_at=expires_at,
        )

    def _generate_attempt(self, session, *, code, seed, actor):
        """Internal entry point; ATTEMPT exams are created only by start_attempt()."""
        return self._generate(
            session, code=code, seed=seed, purpose=GeneratedExam.Purpose.ATTEMPT,
            actor=actor,
        )
