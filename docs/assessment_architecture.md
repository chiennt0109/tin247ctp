# Kiến trúc Assessment — báo cáo khảo sát Giai đoạn 1

> Ngày khảo sát: 2026-07-29. Tài liệu này là kế hoạch trước migration, không tuyên bố
> module đã được triển khai.

## 1. Kết quả khảo sát hệ thống hiện tại

### 1.1. Project và tài khoản

- Đây là project Django hiện hữu với `ROOT_URLCONF = "oj.urls"`; không tạo project hay
  login site mới.
- `AUTH_USER_MODEL` không được override, do đó user model chính xác hiện tại là
  `django.contrib.auth.models.User` (`auth.User`). Assessment phải tham chiếu
  `settings.AUTH_USER_MODEL`/`get_user_model()` để giữ khả năng swappable, không sửa bảng
  tài khoản.
- Xác thực dùng cả `ModelBackend` và django-allauth; Google là một social provider. URL
  tài khoản dùng chung nằm dưới `/accounts/`.
- Nhóm và quyền là cơ chế chuẩn của `django.contrib.auth`: `auth.Group`, `auth.Permission`
  và quan hệ groups/user_permissions có sẵn trên `auth.User`. Repository chưa có model
  lớp học/nhóm riêng. Vì thế `GroupAssessmentAccess` nên FK đến `auth.Group`; nếu sau này
  có nguồn lớp học khác thì cần migration bổ sung, không suy đoán ở Giai đoạn 1.

### 1.2. Admin, giao diện và URL

- Hệ thống dùng duy nhất `django.contrib.admin.site` tại `/admin/`. Template
  `templates/admin/index.html` mở rộng `admin/base_site.html`; assessment phải đăng ký
  vào site này và có thể bổ sung dashboard/menu trong template hiện hữu.
- Admin user hiện được thay bằng `UserAnalyticsAdmin`, vẫn trên cùng admin site.
- Frontend dùng template chung `templates/base.html`, Bootstrap 5.3.3 và Tailwind CDN;
  menu assessment sau này phải mở rộng layout này thay vì tạo shell thứ hai.
- App URLs hiện được include trong `oj/urls.py`. Đích tích hợp dự kiến là
  `/assessment/` và `/api/assessment/` với namespace riêng, nhưng **chưa đăng ký URL** ở
  giai đoạn khảo sát.

### 1.3. PostgreSQL, Redis và RQ

- PostgreSQL được cấu hình từ `DATABASE_URL`, nếu thiếu sẽ dùng cấu hình local.
- `REDIS_URL` và `django_rq` đã có; queues `default` và `judge` dùng chung Redis. Module
  assessment nên có queue riêng (ví dụ `assessment`) hoặc dùng `default` cho tác vụ nhẹ,
  tuyệt đối không làm nghẽn queue `judge`.
- Cache Redis chỉ bật nếu import được `django_redis`, nếu không sẽ fallback locmem. Lock
  phân tán cho attempt không được dựa vào fallback locmem; service lock phải dùng Redis
  client/connection RQ và fail closed ở các thao tác start/submit cần tính duy nhất.
- `django-rq` và `django-redis` đang được dùng/cấu hình nhưng chưa được khai báo đầy đủ
  trong `requirements.txt`; cần chuẩn hóa dependency trước khi triển khai worker mới.

### 1.4. Biên an toàn với judge

Các app `problems`, `submissions`, `contests`, `judge` và queue `judge` phải giữ nguyên.
Assessment sẽ là app độc lập, chỉ dùng chung user/group, hạ tầng và layout. Không tạo FK
từ các bảng lập trình sang assessment và không thay đổi lịch sử submission.

## 2. Trạng thái nguồn master

Chủ sở hữu đã cung cấp Google Sheet `1kyaIfu7NSA4PQ_b6UXb8rRqJYLCdsUNF3AA8_Cf1BbQ`.
Bản export XLSX ngày 2026-07-29 đã được đọc đầy đủ: 24 sheet, 620 câu, 1.980 phương án,
456 nhận định, taxonomy, nguồn, duplicate families, policy, scoring và blueprint. Workbook
không được đưa vào Git. Tên sheet/cột, số liệu, mapping và các bất thường công thức/cached
value được ghi tại `docs/assessment_bank_mapping.md`.

Giai đoạn 1 không còn bị chặn bởi việc thiếu nguồn. Cổng còn lại là chủ sở hữu xác nhận năm
điểm dữ liệu chưa rõ trong tài liệu mapping trước khi chốt schema và tạo migration.

## 3. Đề xuất ranh giới model (chưa phải schema đã duyệt)

Sau khi xác nhận mapping, app `assessment` dự kiến chia các aggregate sau:

1. **Projection nguồn:** `BankQuestion`, `BankQuestionRevision`, `QuestionAsset`,
   `QuestionSyncLog`. Nội dung chỉ đọc trong DMOJ; revision và hash giữ truy vết.
2. **Blueprint có phiên bản:** `ExamBlueprint`, `BlueprintVersion`, `BlueprintSection`,
   `BlueprintSlot`. Bản khóa bất biến; chỉnh sửa tạo version mới.
3. **Scoring có phiên bản:** `ScoringScheme`, `ScoringSchemeVersion`, `ScoringRule`.
   Công thức là cấu hình backend, không nằm trong template/JavaScript.
4. **Session và snapshot:** `ExamSession`, `GeneratedExam`, `GeneratedExamQuestion`,
   `GeneratedExamAsset`. Publish khóa blueprint/scoring và snapshot đề.
5. **Attempt/chấm:** `ExamAttempt`, `AttemptAnswer`, `AttemptEvent`, `GradingResult`;
   liên kết user bằng `settings.AUTH_USER_MODEL`, UUID public, optimistic version và unique
   constraints chống attempt trùng.
6. **Access:** `AssessmentAccessPolicy`, `GroupAssessmentAccess`,
   `UserAssessmentAccess`, `ExamParticipant`, `ExamPermissionOverride`. Resolver trả về
   quyết định kèm nguồn theo ưu tiên user override → exam → group → default.
7. **Audit/job/export:** audit append-only và trạng thái job có idempotency key; mọi tải
   tài liệu nhạy cảm được kiểm quyền backend và ghi audit.

Tên field, enum loại câu, taxonomy, cấu trúc answer/scoring JSON và constraint chỉ được
chốt theo workbook thực tế. Dữ liệu đáp án nên ở revision/snapshot được bảo vệ và không
bao giờ xuất hiện trong serializer/template làm bài.

## 4. Kế hoạch triển khai có cổng kiểm soát

### Cổng A — hoàn tất Giai đoạn 1

- Nhận và đọc toàn bộ master; hoàn thành bảng ánh xạ bằng tên sheet/cột thật.
- Xác nhận taxonomy, enum, khóa, revision, asset, scoring và blueprint với chủ sở hữu.
- Chốt data classification, cách bảo vệ đáp án và chính sách retention/audit.
- Chỉ khi bảng ánh xạ được duyệt mới tạo app/model/migration.

### Giai đoạn 2 — nền tảng dữ liệu

- Tạo app và migration rollback được; thêm index/unique/check constraints.
- Xây parser tách khỏi persistence, validator và dry-run report.
- Apply trong `transaction.atomic()`, lưu revision/audit, không xóa cứng.
- Management command bắt buộc chọn `--dry-run` hoặc `--apply`; upload admin dùng token
  xác nhận dry-run, file tạm ngoài public và kiểm MIME/kích thước/tên.

### Giai đoạn 3 — blueprint và scoring

- Versioning bất biến, editor tích hợp admin, backend validation và availability count.
- Preview/compare/clone; khóa version đã phát hành; scoring simulation ở backend.

### Giai đoạn 4 — session và generator

- Resolver ứng viên theo slot, duplicate group, usage/difficulty và seed tái tạo được.
- Validation tổng thể, snapshot/hash nguyên tử, ba generation modes từ cấu hình.
- Preview/approve/publish có permission và audit.

### Giai đoạn 5–7 — attempt, grading, report và export

- Object permission, Redis lock, optimistic autosave, idempotent submit, server deadline,
  RQ expiry sweep; response làm bài được allow-list và không chứa đáp án.
- Grade từ snapshot scoring; result/answer/solution release là các quyết định riêng.
- Export PDF/editable/XLSX chạy nền, signed access ngắn hạn và download audit.

### Giai đoạn 8 — kiểm thử và triển khai

- Unit/integration/security/concurrency tests theo ma trận nghiệm thu.
- Kiểm query plan/N+1, staging trên bản sao dữ liệu và thử rollback.
- Backup PostgreSQL trước production migration; deploy web/worker, collectstatic và theo
  dõi log/queue. Không chạy production migration từ phiên phát triển này.

## 5. Báo cáo Giai đoạn 1

1. **File tạo/chỉnh sửa:** `docs/assessment_architecture.md` và
   `docs/assessment_bank_mapping.md`.
2. **Migration:** không tạo; master đã được đọc nhưng mapping còn chờ chủ sở hữu xác nhận trước khi chốt schema.
3. **Model/bảng mới:** không có; mới chỉ có đề xuất aggregate để thẩm định.
4. **URL/API mới:** không có; mới xác định điểm tích hợp dự kiến.
5. **Quyền mới:** không có; permission chi tiết sẽ được khai báo trong model sau khi
   mapping/schema được duyệt.
6. **Kiểm tra đã chạy:** tìm nguồn master/biến môi trường; đọc settings, URL, account,
   admin, template, dependency và tham chiếu user/group/RQ.
7. **Kết quả:** xác định `auth.User`, `auth.Group`, allauth, admin site chung, layout chung,
   PostgreSQL/Redis/RQ; đã tải và phân tích đủ 24 sheet của master.
8. **Vấn đề tồn tại:** cần xác nhận cached formula values, nguồn lời giải/asset, short-answer,
   eligibility và legacy score type; dependency RQ/Redis cache cần đồng bộ requirements.
9. **Rủi ro:** nhập formula text thay cached result sẽ làm sai eligibility/difficulty; locmem
   không đủ cho distributed lock; queue judge không được dùng cho assessment; payload phải
   allow-list để không lộ đáp án.
10. **Công việc tiếp theo:** chủ sở hữu duyệt mapping thực tế, sau đó bắt đầu Giai đoạn 2
    bằng một commit riêng.

