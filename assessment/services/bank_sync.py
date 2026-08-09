from collections import Counter

from django.db import transaction
from django.utils import timezone

from assessment.models import (
    AssessmentAuditLog, BankQuestion, BankQuestionRevision, BankSourceFile,
    CurriculumNode, CurriculumOutcome, QuestionAsset, QuestionSyncLog,
)


AVAILABLE_PROCESS_STATUSES = {"READY_FOR_PRACTICE", "READY_FOR_PERIODIC", "READY_FOR_GRADUATION"}
MANUAL_QUESTION_TYPES = {"ESSAY", "PRACTICAL"}


def question_is_structurally_eligible(item):
    """Eligibility shared by preview/persistence; never infer readiness from STATUS."""
    if item["question_type"] == "MCQ_SINGLE":
        return len(item["options"]) == 4 and bool(item.get("answer_key"))
    if item["question_type"] == "TRUE_FALSE_GROUP":
        return len(item["statements"]) == 4 and bool(item.get("answer_key"))
    if item["question_type"] == "SHORT_ANSWER":
        return bool(item.get("answer_key"))
    if item["question_type"] in MANUAL_QUESTION_TYPES:
        return bool(item.get("answer_guide") or item.get("answer_key"))
    return False


class BankSyncService:
    def preview(self, parsed):
        existing = {q.source_question_id: q for q in BankQuestion.objects.all()}
        source_ids = {item["question_id"] for item in parsed.questions}
        counts = Counter()
        for item in parsed.questions:
            counts[f"{item['question_type'].lower()}_valid"] += 1
            current = existing.get(item["question_id"])
            if current is None:
                counts["new"] += 1
                counts[f"{item['question_type'].lower()}_new"] += 1
            elif current.content_hash != item["content_hash"]:
                counts["changed"] += 1
                counts[f"{item['question_type'].lower()}_changed"] += 1
            else:
                counts["unchanged"] += 1
            periodic_eligible = (
                item["process_status"] == "READY_FOR_PERIODIC"
                and question_is_structurally_eligible(item)
            )
            if not periodic_eligible:
                counts["not_periodic_eligible"] += 1
                counts[f"{item['question_type'].lower()}_not_periodic_eligible"] += 1
            else:
                counts[f"{item['question_type'].lower()}_periodic_eligible"] += 1
            if item["process_status"] != "READY_FOR_GRADUATION":
                counts["not_graduation_eligible"] += 1
        counts["retired"] = len(set(existing) - source_ids)
        issue_counts = Counter()
        for error in parsed.errors:
            issue_counts[error.get("code", "UNKNOWN")] += 1
            issue_counts.update(error.get("issues", ()))
        return {
            **counts,
            "valid_questions": len(parsed.questions),
            "structural_errors": len(parsed.errors),
            "warnings": len(parsed.warnings),
            "issue_counts": dict(issue_counts),
            "errors": parsed.errors,
        }

    @transaction.atomic
    def apply(self, parsed, *, initiated_by=None, source_label=None):
        if parsed.has_fatal_errors:
            raise ValueError("Bank contains fatal validation errors; apply aborted")
        report = self.preview(parsed)
        log = QuestionSyncLog.objects.create(
            mode=QuestionSyncLog.Mode.APPLY,
            status=QuestionSyncLog.Status.RUNNING,
            source=source_label or parsed.source_path,
            source_sha256=parsed.source_sha256,
            initiated_by=initiated_by,
        )
        try:
            files = self._sync_files(parsed.rows["FILES"])
            curriculum = self._sync_curriculum(parsed.rows["CURRICULUM"])
            outcomes = self._sync_outcomes(parsed.rows["CURRICULUM_OUTCOMES"], curriculum)
            seen = set()
            for item in parsed.questions:
                seen.add(item["question_id"])
                self._sync_question(item, curriculum, outcomes, files)
            BankQuestion.objects.exclude(source_question_id__in=seen).update(is_available=False)
            log.status = QuestionSyncLog.Status.SUCCEEDED
            log.report = report
            log.completed_at = timezone.now()
            log.save(update_fields=("status", "report", "completed_at"))
            AssessmentAuditLog.objects.create(
                action="SYNC_BANK_APPLY", actor=initiated_by, object_type="QuestionSyncLog",
                object_id=str(log.pk), details={"source_sha256": parsed.source_sha256, **report},
            )
            return log
        except Exception as exc:
            # Atomic rollback removes this log too; callers/tasks should persist failure separately.
            raise ValueError(f"Atomic bank synchronization failed: {exc}") from exc

    @staticmethod
    def _sync_files(rows):
        result = {}
        for row in rows:
            obj, _ = BankSourceFile.objects.update_or_create(
                source_id=str(row["FILE_ID"]), defaults={
                    "name": str(row.get("FILE_NAME") or ""), "mime_type": str(row.get("MIME_TYPE") or ""),
                    "drive_url": str(row.get("DRIVE_URL") or ""), "folder_path": str(row.get("FOLDER_PATH") or ""),
                    "source_group": str(row.get("SOURCE_GROUP") or ""),
                    "note": str(row.get("NOTE") or ""),
                    "checksum": str(row.get("CHECKSUM") or ""), "source_status": str(row.get("FILE_STATUS") or ""),
                    "source_metadata": {},
                },
            )
            result[obj.source_id] = obj
        return result

    @staticmethod
    def _sync_curriculum(rows):
        result = {}
        for row in rows:
            obj, _ = CurriculumNode.objects.update_or_create(
                source_id=str(row["CURRICULUM_ID"]), defaults={
                    "grade": int(row["GRADE"]), "subject": str(row.get("SUBJECT") or ""),
                    "program_version": str(row.get("PROGRAM_VERSION") or ""),
                    "topic_code": str(row.get("TOPIC_CODE") or ""), "topic_name": str(row.get("TOPIC_NAME") or ""),
                    "order_no": int(row.get("ORDER_NO") or 0), "source_status": str(row.get("STATUS") or ""),
                    "source_metadata": {"note": row.get("NOTE")},
                },
            )
            result[obj.source_id] = obj
        return result

    @staticmethod
    def _sync_outcomes(rows, curriculum):
        result = {}
        for row in rows:
            parent = curriculum.get(str(row.get("CURRICULUM_ID")))
            if parent is None:
                raise ValueError(f"Unknown curriculum for outcome {row.get('OUTCOME_ID')}")
            obj, _ = CurriculumOutcome.objects.update_or_create(
                source_id=str(row["OUTCOME_ID"]), defaults={
                    "curriculum": parent, "code": str(row.get("OUTCOME_CODE") or ""),
                    "text": str(row.get("OUTCOME_TEXT") or ""),
                    "cognitive_level": str(row.get("LEVEL") or ""),
                    "source_status": str(row.get("STATUS") or ""),
                    "source_metadata": {"note": row.get("NOTE")},
                },
            )
            result[obj.source_id] = obj
        return result

    @staticmethod
    def _sync_question(item, curriculum, outcomes, files):
        row, mapping = item["row"], item["mapping"]
        question, _ = BankQuestion.objects.update_or_create(
            source_question_id=item["question_id"], defaults={
                "source_code": str(item.get("question_code") or ""), "question_type": item["question_type"],
                "cognitive_level": item["cognitive_level"], "difficulty": item["difficulty"],
                "competency": str(item.get("competency") or ""), "language": str(row.get("LANGUAGE") or "vi"),
                "source_status": str(row.get("STATUS") or ""), "process_status": str(item["process_status"]),
                "use_purpose": str(item.get("use_purpose") or ""), "shuffle_allowed": item["shuffle_allowed"],
                "duplicate_family_id": str(item.get("family_id") or ""),
                # Already typed and validated by WorkbookBankImporter. Apply must
                # never reinterpret raw spreadsheet values differently from dry-run.
                "estimated_time_seconds": item["estimated_time_seconds"],
                "content_hash": item["content_hash"],
                "is_available": (
                    item["process_status"] in AVAILABLE_PROCESS_STATUSES
                    and question_is_structurally_eligible(item)
                ),
                "curriculum": curriculum.get(str(mapping.get("CURRICULUM_ID"))),
                "outcome": outcomes.get(str(mapping.get("OUTCOME_ID"))),
                "source_metadata": {"note": row.get("NOTE"), "classification_basis": row.get("CLASSIFICATION_BASIS"),
                                    "source_physical_status": row.get("__source_status__"),
                                    "formula_fields": item["formula_fields"]},
            },
        )
        protected_answer = {"answer_key": item["answer_key"]}
        if item["question_type"] in MANUAL_QUESTION_TYPES:
            protected_answer.update({
                "answer_guide": item.get("answer_guide") or item.get("answer_key"),
                "manual_score_required": True,
            })
        revision, _ = BankQuestionRevision.objects.get_or_create(
            question=question, content_hash=item["content_hash"], defaults={
                "source_version": item["source_version"], "stem_text": item["stem_text"],
                "options": item["options"], "statements": item["statements"],
                "protected_answer": protected_answer,
                "explanation_source_id": str(row.get("EXPLANATION_ID") or ""),
                "source_metadata": {"source_row": row.get("__row__")},
            },
        )
        if question.current_revision_id != revision.id:
            question.current_revision = revision
            question.save(update_fields=("current_revision",))
        retained_source_file_ids = set()
        for source in item["sources"]:
            source_file = files.get(str(source.get("FILE_ID")))
            if source_file:
                retained_source_file_ids.add(source_file.pk)
                QuestionAsset.objects.update_or_create(
                    question=question,
                    source_file=source_file,
                    defaults={
                        "source_page": str(source.get("SOURCE_PAGE") or ""),
                        "source_section": str(source.get("SOURCE_SECTION") or ""),
                        "source_ref": str(source.get("SOURCE_REF") or ""),
                        "license_note": str(source.get("LICENSE_NOTE") or ""),
                        "source_status": str(source.get("STATUS") or ""),
                    },
                )
        # Remove only relations no longer present in the canonical source. Existing
        # relations above are updated in place, preserving idempotency and identity.
        QuestionAsset.objects.filter(question=question).exclude(
            source_file_id__in=retained_source_file_ids
        ).delete()
