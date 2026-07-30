import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
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


class ExamBlueprint(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        APPROVED = "APPROVED", "Đã duyệt"
        LOCKED = "LOCKED", "Đã khóa"

    name = models.CharField(max_length=255)
    source_blueprint_id = models.CharField(
        max_length=160, null=True, blank=True, unique=True, db_index=True,
    )
    demo_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    is_demo = models.BooleanField(default=False, db_index=True)
    exam_type = models.CharField(max_length=64, db_index=True)
    grade = models.PositiveSmallIntegerField(db_index=True)
    subject = models.CharField(max_length=100, default="Tin học")
    semester = models.CharField(max_length=32, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_assessment_blueprints",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_assessment_blueprints",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class BlueprintVersion(models.Model):
    blueprint = models.ForeignKey(ExamBlueprint, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    duration_minutes = models.PositiveIntegerField()
    expected_question_count = models.PositiveIntegerField()
    expected_total_score = models.DecimalField(max_digits=8, decimal_places=3)
    is_locked = models.BooleanField(default=False, db_index=True)
    source_blueprint_id = models.CharField(max_length=160, blank=True)
    source_snapshot = models.JSONField(default=dict, blank=True)
    validation_report = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_blueprint_versions",
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_blueprint_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("blueprint", "version"), name="assessment_unique_blueprint_version")
        ]
        ordering = ("blueprint", "-version")

    def __str__(self):
        return f"{self.blueprint} v{self.version}"

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk, is_locked=True).exists():
            raise ValidationError("Phiên bản ma trận đã khóa; hãy tạo phiên bản mới.")
        return super().save(*args, **kwargs)


class BlueprintSection(models.Model):
    version = models.ForeignKey(BlueprintVersion, on_delete=models.CASCADE, related_name="sections")
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    instructions = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("version", "code"), name="assessment_unique_section_code")
        ]
        ordering = ("order", "id")

    def clean(self):
        if self.version_id and self.version.is_locked:
            raise ValidationError("Không thể sửa phần thi thuộc ma trận đã khóa.")

    def __str__(self):
        return f"{self.version}: {self.name}"


class BlueprintSlot(models.Model):
    section = models.ForeignKey(BlueprintSection, on_delete=models.CASCADE, related_name="slots")
    order = models.PositiveIntegerField(default=0)
    curriculum = models.ForeignKey(
        CurriculumNode, null=True, blank=True, on_delete=models.PROTECT, related_name="blueprint_slots"
    )
    outcome = models.ForeignKey(
        CurriculumOutcome, null=True, blank=True, on_delete=models.PROTECT, related_name="blueprint_slots"
    )
    question_type = models.CharField(max_length=32)
    cognitive_level = models.CharField(max_length=32, blank=True)
    difficulty = models.PositiveSmallIntegerField(null=True, blank=True)
    competency = models.CharField(max_length=16, blank=True)
    quantity = models.PositiveIntegerField()
    score_per_item = models.DecimalField(max_digits=8, decimal_places=3)
    required_tags = models.JSONField(default=list, blank=True)
    excluded_tags = models.JSONField(default=list, blank=True)
    requires_graduation_eligibility = models.BooleanField(default=False)
    required_process_status = models.CharField(max_length=64, blank=True)
    allow_previously_used = models.BooleanField(default=True)
    max_usage_count = models.PositiveIntegerField(null=True, blank=True)
    reuse_cooldown_days = models.PositiveIntegerField(default=0)
    shortage_priority = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("section__order", "order", "id")

    def clean(self):
        if self.section_id and self.section.version.is_locked:
            raise ValidationError("Không thể sửa slot thuộc ma trận đã khóa.")
        if self.outcome_id and self.curriculum_id and self.outcome.curriculum_id != self.curriculum_id:
            raise ValidationError({"outcome": "YCCD không thuộc chủ đề đã chọn."})
        if self.difficulty is not None and self.difficulty not in range(1, 6):
            raise ValidationError({"difficulty": "Độ khó phải nằm trong khoảng 1–5."})


class ScoringScheme(models.Model):
    name = models.CharField(max_length=255)
    demo_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    is_demo = models.BooleanField(default=False, db_index=True)
    description = models.TextField(blank=True)
    is_default = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_scoring_schemes",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class ScoringSchemeVersion(models.Model):
    scheme = models.ForeignKey(ScoringScheme, on_delete=models.PROTECT, related_name="versions")
    version = models.PositiveIntegerField()
    total_score = models.DecimalField(max_digits=8, decimal_places=3)
    rounding_digits = models.PositiveSmallIntegerField(default=2)
    is_locked = models.BooleanField(default=False, db_index=True)
    source_policy_id = models.CharField(max_length=160, blank=True)
    source_snapshot = models.JSONField(default=dict, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_scoring_versions",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("scheme", "version"), name="assessment_unique_scoring_version")
        ]
        ordering = ("scheme", "-version")

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk, is_locked=True).exists():
            raise ValidationError("Phiên bản chấm điểm đã khóa; hãy tạo phiên bản mới.")
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.scheme} v{self.version}"


class ScoringRule(models.Model):
    version = models.ForeignKey(ScoringSchemeVersion, on_delete=models.CASCADE, related_name="rules")
    question_type = models.CharField(max_length=32)
    rule_code = models.CharField(max_length=100)
    max_score = models.DecimalField(max_digits=8, decimal_places=3)
    configuration = models.JSONField(default=dict)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("version", "question_type"), name="assessment_unique_scoring_type")
        ]
        ordering = ("order", "id")

    def clean(self):
        if self.version_id and self.version.is_locked:
            raise ValidationError("Không thể sửa quy tắc thuộc phiên bản đã khóa.")


class ExamSession(models.Model):
    class ExamType(models.TextChoices):
        PRACTICE = "PRACTICE", "Luyện tập"
        REGULAR = "REGULAR", "Kiểm tra thường xuyên"
        PERIODIC = "PERIODIC", "Kiểm tra định kỳ"
        GRADUATION = "GRADUATION", "Thi thử tốt nghiệp"
        CUSTOM = "CUSTOM", "Tùy chỉnh"

    class GenerationMode(models.TextChoices):
        ON_DEMAND_INDIVIDUAL = "ON_DEMAND_INDIVIDUAL", "Sinh riêng khi bắt đầu"
        ON_DEMAND_CODE_POOL = "ON_DEMAND_CODE_POOL", "Cấp mã từ nhóm khi bắt đầu"
        FIXED_EXAM = "FIXED_EXAM", "Đề cố định"

    class AccessMode(models.TextChoices):
        ALL_USERS = "ALL_USERS", "Mọi tài khoản"
        SELECTED_GROUPS = "SELECTED_GROUPS", "Nhóm được chọn"
        SELECTED_GRADES = "SELECTED_GRADES", "Khối được chọn"
        SELECTED_USERS = "SELECTED_USERS", "Tài khoản được chọn"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Nháp"
        SCHEDULED = "SCHEDULED", "Đã lên lịch"
        OPEN = "OPEN", "Đang mở"
        CLOSED = "CLOSED", "Đã đóng"
        PUBLISHED = "PUBLISHED", "Đã công bố"
        CANCELLED = "CANCELLED", "Đã hủy"

    class ReleaseMode(models.TextChoices):
        NEVER = "NEVER", "Không bao giờ"
        AFTER_SUBMIT = "IMMEDIATELY_AFTER_SUBMIT", "Ngay sau khi nộp"
        AFTER_ALL = "AFTER_USER_FINISHES_ALL_ATTEMPTS", "Sau khi hết lượt"
        AFTER_CLOSE = "AFTER_EXAM_CLOSES", "Sau khi đóng kỳ thi"
        AT_TIME = "AT_SPECIFIC_TIME", "Tại thời điểm cấu hình"
        MANUAL = "MANUAL_RELEASE", "Công bố thủ công"

    class AttemptResultMode(models.TextChoices):
        FIRST = "FIRST", "Lần đầu"
        LAST = "LAST", "Lần cuối"
        HIGHEST = "HIGHEST", "Cao nhất"
        AVERAGE = "AVERAGE", "Trung bình"
        TEACHER = "TEACHER_SELECTED", "Giáo viên chọn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.SlugField(max_length=180, unique=True)
    name = models.CharField(max_length=255)
    demo_key = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        unique=True,
        db_index=True,
    )
    is_demo = models.BooleanField(default=False, db_index=True)
    exam_type = models.CharField(max_length=32, choices=ExamType.choices)
    blueprint_version = models.ForeignKey(BlueprintVersion, on_delete=models.PROTECT, related_name="exam_sessions")
    scoring_version = models.ForeignKey(
        ScoringSchemeVersion, on_delete=models.PROTECT, related_name="exam_sessions"
    )
    opens_at = models.DateTimeField(db_index=True)
    closes_at = models.DateTimeField(db_index=True)
    duration_minutes = models.PositiveIntegerField()
    max_attempts = models.PositiveIntegerField(default=1)
    attempt_result_mode = models.CharField(
        max_length=32, choices=AttemptResultMode.choices, default=AttemptResultMode.HIGHEST
    )
    next_attempt_delay_minutes = models.PositiveIntegerField(default=0)
    shuffle_questions = models.BooleanField(default=True)
    shuffle_options = models.BooleanField(default=True)
    code_count = models.PositiveIntegerField(default=1)
    generation_mode = models.CharField(
        max_length=40, choices=GenerationMode.choices,
        default=GenerationMode.ON_DEMAND_INDIVIDUAL,
    )
    access_mode = models.CharField(max_length=32, choices=AccessMode.choices, default=AccessMode.ALL_USERS)
    access_groups = models.ManyToManyField("auth.Group", blank=True, related_name="assessment_sessions")
    access_grades = models.JSONField(default=list, blank=True)
    score_release_mode = models.CharField(max_length=40, choices=ReleaseMode.choices, default=ReleaseMode.MANUAL)
    score_release_at = models.DateTimeField(null=True, blank=True)
    answer_release_mode = models.CharField(max_length=40, choices=ReleaseMode.choices, default=ReleaseMode.NEVER)
    answer_release_at = models.DateTimeField(null=True, blank=True)
    solution_release_mode = models.CharField(
        max_length=40, choices=ReleaseMode.choices, default=ReleaseMode.NEVER,
    )
    solution_release_at = models.DateTimeField(null=True, blank=True)
    release_solutions = models.BooleanField(default=False)
    allow_exam_download = models.BooleanField(default=False)
    allow_blueprint_download = models.BooleanField(default=False)
    allow_review = models.BooleanField(default=False)
    allow_retry_after_answers = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_exam_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)
    results_released_at = models.DateTimeField(null=True, blank=True)
    answers_released_at = models.DateTimeField(null=True, blank=True)
    solutions_released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("status", "opens_at", "closes_at"), name="assessment_session_window_idx")]

    def clean(self):
        if self.closes_at <= self.opens_at:
            raise ValidationError({"closes_at": "Thời gian đóng phải sau thời gian mở."})
        if self.generation_mode == self.GenerationMode.ON_DEMAND_CODE_POOL and self.code_count < 2:
            raise ValidationError({"code_count": "Nhóm mã đề cần ít nhất hai mã."})
        if self.answer_release_mode == self.ReleaseMode.AT_TIME and not self.answer_release_at:
            raise ValidationError({"answer_release_at": "Phải cấu hình thời điểm công bố đáp án."})
        if self.score_release_mode == self.ReleaseMode.AT_TIME and not self.score_release_at:
            raise ValidationError({"score_release_at": "Phải cấu hình thời điểm công bố điểm."})
        if self.solution_release_mode == self.ReleaseMode.AT_TIME and not self.solution_release_at:
            raise ValidationError({"solution_release_at": "Phải cấu hình thời điểm công bố lời giải."})

    def __str__(self):
        return self.name


class GeneratedExam(models.Model):
    class Purpose(models.TextChoices):
        ATTEMPT = "ATTEMPT", "Attempt"
        PREVIEW = "PREVIEW", "Preview"

    session = models.ForeignKey(ExamSession, on_delete=models.PROTECT, related_name="generated_exams")
    code = models.CharField(max_length=64)
    seed = models.CharField(max_length=128)
    blueprint_version = models.ForeignKey(BlueprintVersion, on_delete=models.PROTECT)
    scoring_version = models.ForeignKey(ScoringSchemeVersion, on_delete=models.PROTECT)
    total_score = models.DecimalField(max_digits=8, decimal_places=3)
    validation_report = models.JSONField(default=dict)
    exam_hash = models.CharField(max_length=64, db_index=True)
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="generated_assessment_exams",
    )
    generated_at = models.DateTimeField(auto_now_add=True)
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(purpose__in=("ATTEMPT", "PREVIEW")),
                name="assessment_generated_exam_valid_purpose",
            ),
        ]
        ordering = ("session", "code")


class GeneratedExamQuestion(models.Model):
    exam = models.ForeignKey(GeneratedExam, on_delete=models.CASCADE, related_name="questions")
    bank_question = models.ForeignKey(BankQuestion, on_delete=models.PROTECT)
    bank_revision = models.ForeignKey(BankQuestionRevision, on_delete=models.PROTECT)
    blueprint_slot = models.ForeignKey(BlueprintSlot, on_delete=models.PROTECT)
    order = models.PositiveIntegerField()
    question_id_snapshot = models.CharField(max_length=160)
    source_version_snapshot = models.CharField(max_length=64)
    stem_snapshot = models.TextField()
    options_snapshot = models.JSONField(default=list, blank=True)
    statements_snapshot = models.JSONField(default=list, blank=True)
    protected_answer_snapshot = models.TextField()
    option_order = models.JSONField(default=list, blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=3)
    content_hash_snapshot = models.CharField(max_length=64)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("exam", "order"), name="assessment_unique_exam_question_order"),
            models.UniqueConstraint(fields=("exam", "bank_question"), name="assessment_unique_exam_question"),
        ]
        ordering = ("order",)


class GeneratedExamAsset(models.Model):
    exam_question = models.ForeignKey(
        GeneratedExamQuestion, on_delete=models.CASCADE, related_name="assets"
    )
    source_file_id_snapshot = models.CharField(max_length=160)
    name_snapshot = models.CharField(max_length=500)
    mime_type_snapshot = models.CharField(max_length=255, blank=True)
    source_page_snapshot = models.CharField(max_length=128, blank=True)
    checksum_snapshot = models.CharField(max_length=128, blank=True)


class ExamParticipant(models.Model):
    session = models.ForeignKey(ExamSession, on_delete=models.CASCADE, related_name="participants")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="assessment_participations"
    )
    is_enabled = models.BooleanField(default=True)
    can_access = models.BooleanField(default=True)
    can_view_answers = models.BooleanField(default=False)
    can_view_solutions = models.BooleanField(default=False)
    can_download_exam = models.BooleanField(default=False)
    can_download_blueprint = models.BooleanField(default=False)
    make_up_allowed = models.BooleanField(default=False)
    allow_after_deadline = models.BooleanField(default=False)
    extra_time_minutes = models.PositiveIntegerField(default=0)
    max_attempts_override = models.PositiveIntegerField(null=True, blank=True)
    available_from = models.DateTimeField(null=True, blank=True)
    available_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("session", "user"), name="assessment_unique_exam_participant")
        ]


class ExamAttempt(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "IN_PROGRESS", "Đang làm"
        SUBMITTED = "SUBMITTED", "Đã nộp"
        AUTO_SUBMITTED = "AUTO_SUBMITTED", "Tự động nộp"
        GRADED = "GRADED", "Đã chấm"
        INVALIDATED = "INVALIDATED", "Vô hiệu hóa"
        EXPIRED = "EXPIRED", "Hết hạn"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="assessment_attempts"
    )
    session = models.ForeignKey(ExamSession, on_delete=models.PROTECT, related_name="attempts")
    attempt_number = models.PositiveIntegerField()
    generated_exam = models.OneToOneField(
        GeneratedExam, null=True, blank=True, on_delete=models.PROTECT, related_name="attempt"
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    data_version = models.PositiveIntegerField(default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.IN_PROGRESS, db_index=True
    )
    invalidation_reason = models.TextField(blank=True)
    score = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    graded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "session", "attempt_number"),
                name="assessment_unique_attempt_number",
            ),
            models.UniqueConstraint(
                fields=("user", "session"), condition=models.Q(status="IN_PROGRESS"),
                name="assessment_one_in_progress_attempt",
            ),
        ]
        ordering = ("-started_at",)


class AttemptAnswer(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.CASCADE, related_name="answers")
    exam_question = models.ForeignKey(
        GeneratedExamQuestion, on_delete=models.PROTECT, related_name="attempt_answers"
    )
    answer = models.JSONField(default=dict, blank=True)
    flagged_for_review = models.BooleanField(default=False)
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "exam_question"), name="assessment_unique_attempt_answer"
            )
        ]


class GradingResult(models.Model):
    attempt = models.ForeignKey(ExamAttempt, on_delete=models.PROTECT, related_name="grading_results")
    sequence = models.PositiveIntegerField()
    scoring_version = models.ForeignKey(ScoringSchemeVersion, on_delete=models.PROTECT)
    total_score = models.DecimalField(max_digits=8, decimal_places=3)
    max_score = models.DecimalField(max_digits=8, decimal_places=3)
    correct_count = models.PositiveIntegerField(default=0)
    incorrect_count = models.PositiveIntegerField(default=0)
    blank_count = models.PositiveIntegerField(default=0)
    detail = models.JSONField(default=list)
    is_current = models.BooleanField(default=True, db_index=True)
    graded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assessment_grading_results",
    )
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("attempt", "sequence"), name="assessment_unique_grading_sequence",
            ),
            models.UniqueConstraint(
                fields=("attempt",), condition=models.Q(is_current=True),
                name="assessment_one_current_grading_result",
            ),
        ]
        ordering = ("-sequence",)
