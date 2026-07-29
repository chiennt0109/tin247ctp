from django.conf import settings
from django.db import models


class SourceStatus(models.TextChoices):
    ACTIVE = "ACTIVE", "Active"
    ARCHIVED = "ARCHIVED", "Archived"
    OTHER = "OTHER", "Other"


class CurriculumNode(models.Model):
    source_id = models.CharField(max_length=128, unique=True)
    grade = models.PositiveSmallIntegerField(db_index=True)
    subject = models.CharField(max_length=100)
    program_version = models.CharField(max_length=100)
    topic_code = models.CharField(max_length=32)
    topic_name = models.CharField(max_length=500)
    order_no = models.PositiveIntegerField(default=0)
    source_status = models.CharField(max_length=32)
    source_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("grade", "order_no", "source_id")

    def __str__(self):
        return f"{self.source_id} — {self.topic_name}"


class CurriculumOutcome(models.Model):
    source_id = models.CharField(max_length=160, unique=True)
    curriculum = models.ForeignKey(CurriculumNode, on_delete=models.PROTECT, related_name="outcomes")
    code = models.CharField(max_length=64)
    text = models.TextField()
    cognitive_level = models.CharField(max_length=32)
    source_status = models.CharField(max_length=32)
    source_metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.source_id


class BankSourceFile(models.Model):
    source_id = models.CharField(max_length=160, unique=True)
    name = models.CharField(max_length=500)
    mime_type = models.CharField(max_length=255, blank=True)
    drive_url = models.URLField(max_length=1000, blank=True)
    folder_path = models.TextField(blank=True)
    checksum = models.CharField(max_length=128, blank=True)
    source_status = models.CharField(max_length=32, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name


class BankQuestion(models.Model):
    source_question_id = models.CharField(max_length=160, unique=True, db_index=True)
    source_code = models.CharField(max_length=160, blank=True)
    question_type = models.CharField(max_length=32, db_index=True)
    cognitive_level = models.CharField(max_length=32, db_index=True)
    difficulty = models.PositiveSmallIntegerField(db_index=True)
    competency = models.CharField(max_length=16, blank=True)
    language = models.CharField(max_length=16, default="vi")
    source_status = models.CharField(max_length=32, db_index=True)
    process_status = models.CharField(max_length=64, db_index=True)
    use_purpose = models.CharField(max_length=64, db_index=True)
    shuffle_allowed = models.BooleanField(default=False)
    duplicate_family_id = models.CharField(max_length=160, blank=True, db_index=True)
    estimated_time_seconds = models.PositiveIntegerField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, db_index=True)
    is_available = models.BooleanField(default=False, db_index=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(auto_now=True)
    current_revision = models.ForeignKey(
        "BankQuestionRevision", null=True, blank=True, on_delete=models.PROTECT,
        related_name="current_for_questions",
    )
    curriculum = models.ForeignKey(
        CurriculumNode, null=True, blank=True, on_delete=models.PROTECT, related_name="questions"
    )
    outcome = models.ForeignKey(
        CurriculumOutcome, null=True, blank=True, on_delete=models.PROTECT, related_name="questions"
    )

    class Meta:
        ordering = ("source_question_id",)

    def __str__(self):
        return self.source_question_id


class BankQuestionRevision(models.Model):
    question = models.ForeignKey(BankQuestion, on_delete=models.PROTECT, related_name="revisions")
    source_version = models.CharField(max_length=64)
    content_hash = models.CharField(max_length=64, db_index=True)
    stem_text = models.TextField()
    options = models.JSONField(default=list, blank=True)
    statements = models.JSONField(default=list, blank=True)
    # Never expose through student serializers/views. Admin also treats this as read-only.
    protected_answer = models.JSONField()
    explanation_source_id = models.CharField(max_length=160, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("question", "content_hash"), name="assessment_unique_question_hash")
        ]
        ordering = ("-synced_at", "-id")

    def __str__(self):
        return f"{self.question_id}@{self.source_version}"


class QuestionAsset(models.Model):
    question = models.ForeignKey(BankQuestion, on_delete=models.PROTECT, related_name="assets")
    source_file = models.ForeignKey(BankSourceFile, on_delete=models.PROTECT, related_name="question_assets")
    source_page = models.CharField(max_length=128, blank=True)
    source_section = models.CharField(max_length=255, blank=True)
    source_ref = models.TextField(blank=True)
    license_note = models.TextField(blank=True)
    source_status = models.CharField(max_length=32, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("question", "source_file"), name="assessment_unique_question_source")
        ]


class QuestionSyncLog(models.Model):
    class Mode(models.TextChoices):
        DRY_RUN = "DRY_RUN", "Dry run"
        APPLY = "APPLY", "Apply"

    class Status(models.TextChoices):
        RUNNING = "RUNNING", "Running"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    mode = models.CharField(max_length=16, choices=Mode.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.RUNNING)
    source = models.CharField(max_length=1000)
    source_sha256 = models.CharField(max_length=64, blank=True)
    report = models.JSONField(default=dict, blank=True)
    error_summary = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assessment_sync_logs",
    )

    class Meta:
        ordering = ("-started_at",)


class AssessmentAuditLog(models.Model):
    action = models.CharField(max_length=100, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assessment_audit_entries",
    )
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=160, blank=True)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-created_at",)
        permissions = [
            ("sync_bank", "Can synchronize the assessment bank"),
            ("view_dashboard", "Can view assessment dashboard"),
            ("view_audit_log", "Can view assessment audit log"),
            ("manage_blueprint", "Can manage assessment blueprints"),
            ("approve_blueprint", "Can approve assessment blueprints"),
            ("manage_scoring", "Can manage assessment scoring"),
            ("create_exam", "Can create assessment exams"),
            ("publish_exam", "Can publish assessment exams"),
            ("manage_participants", "Can manage assessment participants"),
            ("view_results", "Can view assessment results"),
            ("release_results", "Can release assessment results"),
            ("release_answers", "Can release assessment answers"),
            ("export_exam", "Can export assessment exams"),
            ("export_blueprint", "Can export assessment blueprints"),
            ("manage_access", "Can manage assessment access"),
            ("invalidate_attempt", "Can invalidate assessment attempts"),
            ("regrade_attempts", "Can regrade assessment attempts"),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Assessment audit entries are immutable")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError("Assessment audit entries are immutable")
