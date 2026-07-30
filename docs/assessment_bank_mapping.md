# Ánh xạ ngân hàng câu hỏi Assessment

> Trạng thái: **Giai đoạn 1 — đã đọc nguồn, chờ xác nhận mapping trước migration**
> Ngày khảo sát: 2026-07-29
> Nguồn chuẩn: Google Sheet `1kyaIfu7NSA4PQ_b6UXb8rRqJYLCdsUNF3AA8_Cf1BbQ`

## 1. Nguồn và phương pháp khảo sát

Workbook được tải từ URL Google Sheets do chủ sở hữu cung cấp bằng endpoint export XLSX
(chỉ đọc). Bản tải ngày 2026-07-29 có kích thước 862.699 byte, là XLSX hợp lệ, gồm 24
sheet đều visible. Không lưu workbook hay đáp án vào Git.

Phân tích thực hiện hai lượt: `data_only=False` để nhận diện công thức và
`data_only=True` để đọc cached result. Đây là yêu cầu quan trọng cho importer: nhiều cột
nghiệp vụ trong `QUESTIONS` là công thức Google Sheets được XLSX biểu diễn bằng
`_xlfn`/`__xludf.DUMMYFUNCTION`; parser không được nhập chuỗi công thức thay cho kết quả.
Importer phải ưu tiên giá trị đã tính từ Sheets API hoặc cached value, đồng thời báo lỗi nếu
không có cached result hợp lệ.

## 2. Danh mục sheet thực tế

Số dòng dưới đây không tính hàng tiêu đề và không tính các hàng chỉ có format/validation.

| Sheet | Dòng dữ liệu | Khóa chính/cột thực tế | Vai trò |
|---|---:|---|---|
| `TONG_QUAN` | 1 | `PROJECT_ID` | Metadata project/batch |
| `FILES` | 15 | `FILE_ID` | File/asset nguồn trên Drive |
| `CURRICULUM` | 117 | `CURRICULUM_ID` | Khối, chương trình, chủ đề/bài |
| `CURRICULUM_OUTCOMES` | 131 | `OUTCOME_ID` | Yêu cầu cần đạt |
| `TEACHING_PLANS` | 6 | `PLAN_ID` | Phiên bản kế hoạch dạy học |
| `TEACHING_PLAN_ITEMS` | 999 (180 có nội dung nghiệp vụ) | `PLAN_ITEM_ID` | Tiết/bài và quyền dùng kiểm tra |
| `QUESTIONS` | 620 | `QUESTION_ID` | Câu hỏi chuẩn |
| `OPTIONS` | 1.980 | `OPTION_ID` | Phương án MCQ |
| `STATEMENTS` | 456 | `STATEMENT_ID` | Bốn nhận định của câu đúng/sai |
| `QUESTION_CURRICULUM` | 620 | `QUESTION_CURRICULUM_ID` | Liên kết câu–chủ đề–YCCD |
| `QUESTION_SOURCES` | 620 | `QUESTION_SOURCE_ID` | Provenance của câu |
| `DUPLICATES` | 114 | `DUPLICATE_ID` | Quan hệ trùng/gần trùng/family |
| `POLICY_PROFILES` | 2 | `POLICY_PROFILE_ID` | Chính sách kỳ thi tốt nghiệp |
| `SCORE_RULES` | 4 | `SCORE_RULE_ID` | Quy tắc chấm theo policy/type |
| `BLUEPRINTS` | 4 | `BLUEPRINT_ID` | Ma trận có version |
| `BLUEPRINT_CELLS` | 100 | `BLUEPRINT_CELL_ID` | Dòng/ràng buộc ma trận |
| `BLUEPRINT_SLOTS` | 112 | `BLUEPRINT_SLOT_ID` | Slot chọn câu cụ thể |
| `EXAMS` | 0 | `EXAM_ID` | Đề nguồn (schema sẵn, chưa có dữ liệu) |
| `EXAM_ITEMS` | 0 | `EXAM_ITEM_ID` | Câu trong đề nguồn |
| `USAGE_LOG` | 0 | `USAGE_ID` | Nhật ký sử dụng câu |
| `RAW_PENDING` | 624 | `RAW_ID` | Staging nội dung chưa/đã chuẩn hóa |
| `EXPORT_TEMPLATES` | 0 | `EXPORT_TEMPLATE_ID` | Mẫu xuất tài liệu |
| `QUY_UOC` | 49 | `CONFIG_KEY` | Quy ước vận hành có thẩm quyền |
| `AUDIT_LOG` | 800 | `AUDIT_ID` | Audit của master |

Quy ước `UNIQUE_KEY_RULE` trong `QUY_UOC` xác nhận cột đầu tiên của mỗi bảng là khóa duy
nhất, bắt buộc, không trùng.

## 3. Header thực tế theo nhóm

### 3.1. Nội dung, taxonomy và nguồn

- `QUESTIONS`: `QUESTION_ID`, `QUESTION_CODE`, `QUESTION_TYPE`, `COGNITIVE_LEVEL`,
  `STEM_TEXT`, `ANSWER_KEY`, `EXPLANATION_ID`, `STATUS`, `VERSION`, `LANGUAGE`,
  `CREATED_AT`, `UPDATED_AT`, `NOTE`, `DIFFICULTY`, `COMPETENCY`,
  `ESTIMATED_TIME_SEC`, `USE_PURPOSE`, `SHUFFLE_ALLOWED`, `FAMILY_ID`,
  `PROCESS_STATUS`, `CLASSIFICATION_BASIS`.
- `OPTIONS`: `OPTION_ID`, `QUESTION_ID`, `OPTION_LABEL`, `OPTION_TEXT`, `IS_CORRECT`,
  `ORDER_NO`, `STATUS`.
- `STATEMENTS`: `STATEMENT_ID`, `QUESTION_ID`, `STATEMENT_LABEL`, `STATEMENT_TEXT`,
  `TRUTH_VALUE`, `ORDER_NO`, `STATUS`, `COGNITIVE_LEVEL`, `DIFFICULTY`,
  `CLASSIFICATION_BASIS`.
- `CURRICULUM`: `CURRICULUM_ID`, `GRADE`, `SUBJECT`, `PROGRAM_VERSION`, `TOPIC_CODE`,
  `TOPIC_NAME`, `ORDER_NO`, `STATUS`, `NOTE`.
- `CURRICULUM_OUTCOMES`: `OUTCOME_ID`, `CURRICULUM_ID`, `OUTCOME_CODE`,
  `OUTCOME_TEXT`, `LEVEL`, `STATUS`, `NOTE`.
- `QUESTION_CURRICULUM`: `QUESTION_CURRICULUM_ID`, `QUESTION_ID`, `CURRICULUM_ID`,
  `OUTCOME_ID`, `WEIGHT`, `STATUS`, `NOTE`.
- `QUESTION_SOURCES`: `QUESTION_SOURCE_ID`, `QUESTION_ID`, `FILE_ID`, `SOURCE_PAGE`,
  `SOURCE_SECTION`, `SOURCE_REF`, `LICENSE_NOTE`, `STATUS`.
- `FILES`: `FILE_ID`, `FILE_NAME`, `MIME_TYPE`, `PARENT_FOLDER_ID`, `FOLDER_PATH`,
  `DRIVE_URL`, `SOURCE_GROUP`, `FILE_STATUS`, `CHECKSUM`, `CREATED_AT`, `MODIFIED_AT`,
  `INDEXED_AT`, `NOTE`.
- `DUPLICATES`: `DUPLICATE_ID`, `QUESTION_ID_A`, `QUESTION_ID_B`, `MATCH_SCORE`,
  `MATCH_TYPE`, `REVIEW_STATUS`, `DECISION`, `REVIEWED_BY`, `REVIEWED_AT`, `NOTE`,
  `FAMILY_ID`.

### 3.2. Kế hoạch, policy, scoring và blueprint

- `TEACHING_PLANS`: `PLAN_ID`, `PLAN_NAME`, `SCHOOL_YEAR`, `GRADE`, `SUBJECT`,
  `VERSION`, `STATUS`, `SOURCE_FILE_ID`, `CREATED_AT`, `UPDATED_AT`, `NOTE`,
  `SEMESTER`, `ORIENTATION`, `SCHOOL_NAME`, `APPROVED_BY`, `APPROVED_AT`.
- `TEACHING_PLAN_ITEMS`: `PLAN_ITEM_ID`, `PLAN_ID`, `WEEK_NO`, `PERIOD_NO`,
  `TOPIC_CODE`, `LESSON_NAME`, `OUTCOME_ID`, `DURATION_MIN`, `STATUS`, `NOTE`,
  `COMPLETED_AT`, `ALLOWED_FOR_TESTING`, `APPROVED_BY`, `APPROVED_AT`.
- `POLICY_PROFILES`: `POLICY_PROFILE_ID`, `PROFILE_NAME`, `EFFECTIVE_FROM`,
  `EFFECTIVE_TO`, `STATUS`, `DESCRIPTION`.
- `SCORE_RULES`: `SCORE_RULE_ID`, `POLICY_PROFILE_ID`, `QUESTION_TYPE`, `RULE_CODE`,
  `RULE_DESCRIPTION`, `MAX_SCORE`, `PARTIAL_SCORE_ALLOWED`, `STATUS`.
- `BLUEPRINTS`: `BLUEPRINT_ID`, `BLUEPRINT_NAME`, `EXAM_TYPE`, `GRADE`, `SUBJECT`,
  `POLICY_PROFILE_ID`, `TOTAL_QUESTIONS`, `TOTAL_SCORE`, `DURATION_MIN`, `VERSION`,
  `STATUS`, `NOTE`, `SEMESTER`, `ORIENTATION`, `TEACHING_PLAN_ID`, `APPROVED_AT`,
  `SNAPSHOT_REF`.
- `BLUEPRINT_CELLS`: `BLUEPRINT_CELL_ID`, `BLUEPRINT_ID`, `CURRICULUM_ID`,
  `OUTCOME_ID`, `QUESTION_TYPE`, `COGNITIVE_LEVEL`, `REQUIRED_COUNT`,
  `SCORE_PER_ITEM`, `STATUS`, `DIFFICULTY`, `COMPETENCY`, `NOTE`.
- `BLUEPRINT_SLOTS`: `BLUEPRINT_SLOT_ID`, `BLUEPRINT_ID`, `SLOT_NO`,
  `BLUEPRINT_CELL_ID`, `QUESTION_ID`, `STATUS`, `NOTE`.

### 3.3. Đề, usage và vận hành

- `EXAMS`: `EXAM_ID`, `EXAM_CODE`, `EXAM_NAME`, `EXAM_TYPE`, `SCHOOL_YEAR`,
  `EXAM_DATE`, `DURATION_MIN`, `BLUEPRINT_ID`, `VERSION`, `STATUS`, `NOTE`,
  `BLUEPRINT_VERSION`, `RANDOM_SEED`, `GENERATED_AT`, `SNAPSHOT_REF`.
- `EXAM_ITEMS`: `EXAM_ITEM_ID`, `EXAM_ID`, `ITEM_NO`, `QUESTION_ID`, `SCORE`,
  `QUESTION_ORDER`, `OPTION_ORDER_SEED`, `STATUS`, `NOTE`, `QUESTION_VERSION`,
  `BLUEPRINT_SLOT_ID`, `OPTION_ORDER`, `RANDOM_SEED`.
- `USAGE_LOG`: `USAGE_ID`, `QUESTION_ID`, `EXAM_ID`, `USED_AT`, `PURPOSE`, `RESULT`,
  `USER_EMAIL`, `BATCH_ID`, `NOTE`.
- `RAW_PENDING`: `RAW_ID`, `SOURCE_FILE_ID`, `SOURCE_PAGE`, `RAW_TEXT`,
  `DETECTED_TYPE`, `PROCESS_STATUS`, `ASSIGNED_TO`, `BATCH_ID`, `CREATED_AT`, `NOTE`.
- `EXPORT_TEMPLATES`: `EXPORT_TEMPLATE_ID`, `TEMPLATE_NAME`, `OUTPUT_FORMAT`,
  `TARGET_SYSTEM`, `FILE_ID`, `VERSION`, `STATUS`, `NOTE`.
- `AUDIT_LOG`: `AUDIT_ID`, `BATCH_ID`, `TIMESTAMP`, `ACTION`, `OBJECT_TYPE`,
  `OBJECT_ID`, `OBJECT_NAME`, `RESULT`, `DETAILS`, `ACTOR`.

## 4. Ánh xạ Excel → Django projection

| Nguồn thực tế | Trường Django đề xuất | Yêu cầu | Xử lý |
|---|---|---|---|
| `QUESTIONS.QUESTION_ID` | `BankQuestion.source_question_id` | Bắt buộc | unique, immutable natural key |
| `QUESTION_CODE` | `source_code` | Tùy chọn | giữ nguyên |
| `QUESTION_TYPE` | `question_type` | Bắt buộc | enum master, không dùng enum legacy |
| `COGNITIVE_LEVEL` | `cognitive_level` | Bắt buộc | `BIET/HIEU/VANDUNG` |
| `STEM_TEXT` | revision `stem_text` | Bắt buộc | normalize line ending, không đổi nội dung |
| `ANSWER_KEY` | revision `protected_answer` | Bắt buộc | mã hóa/bảo vệ; cấm serializer làm bài |
| `EXPLANATION_ID` | revision `source_explanation_id` | Tùy chọn | hiện 620/620 rỗng; chưa có sheet explanation |
| `STATUS` | `source_status` | Bắt buộc | hiện `ACTIVE/ARCHIVED` |
| `VERSION` | revision `source_version` | Bắt buộc | chuẩn hóa numeric thành string canonical |
| `LANGUAGE` | `language` | Bắt buộc | hiện toàn bộ `vi` |
| `CREATED_AT/UPDATED_AT` | source timestamps | Tùy chọn | parse ISO/date, giữ raw khi lỗi |
| `NOTE` | revision `source_metadata.note` | Tùy chọn | không dùng text tự do làm quyền nếu có field chuẩn |
| `DIFFICULTY` | `difficulty` | Bắt buộc | cached integer 1–5; không nhập formula text |
| `COMPETENCY` | `competency` | Bắt buộc | `NLa..NLe`; hiện không có `NLe` trong cached data |
| `ESTIMATED_TIME_SEC` | `estimated_time_seconds` | Tùy chọn | integer dương |
| `USE_PURPOSE` | `source_use_purpose` | Bắt buộc | cached `PRACTICE/GRADUATION/NONE` hiện tại |
| `SHUFFLE_ALLOWED` | `shuffle_allowed` | Bắt buộc | normalize boolean/string/cached formula |
| `FAMILY_ID` | `duplicate_family_id` | Bắt buộc theo quy ước | một đề tối đa một family |
| `PROCESS_STATUS` | `process_status` | Bắt buộc | eligibility dùng field này, không chỉ `STATUS` |
| `CLASSIFICATION_BASIS` | metadata | Tùy chọn | giữ cached result và raw formula metadata |
| `OPTIONS.*` | revision `options_snapshot` | MCQ bắt buộc | đúng 4 nhãn A–D, order unique, đúng 1 đáp án |
| `STATEMENTS.*` | revision `statements_snapshot` | TF bắt buộc | đúng 4 nhãn a–d, mỗi nhận định có truth value |
| `QUESTION_CURRICULUM.*` | taxonomy relation | Bắt buộc | FK câu, curriculum, outcome phải tồn tại |
| `CURRICULUM.GRADE` | `grade` qua taxonomy | Bắt buộc | integer 10/11/12 từ numeric Excel |
| `CURRICULUM.TOPIC_CODE/NAME` | topic fields | Bắt buộc | giữ code A–G và tên thật |
| `CURRICULUM_OUTCOMES.*` | outcome projection | Bắt buộc | outcome phải thuộc đúng curriculum |
| `QUESTION_SOURCES.*` + `FILES.*` | `QuestionAsset/source_metadata` | Bắt buộc provenance | không public Drive/internal path trực tiếp |
| `DUPLICATES.*` | duplicate relations | Tùy chọn theo câu | `EXACT_DUPLICATE/NEAR_DUPLICATE/SAME_TEMPLATE` |
| `POLICY_PROFILES.*` | scoring/policy source revision | Có điều kiện | chỉ `APPROVED` dùng tự động |
| `SCORE_RULES.*` | `ScoringRule` source projection | Có điều kiện | map legacy type sang canonical type |
| `BLUEPRINTS.*` | `ExamBlueprint/BlueprintVersion` | Có điều kiện | ID + VERSION định danh version nguồn |
| `BLUEPRINT_CELLS.*` | `BlueprintSlot` criteria | Có điều kiện | count/score/taxonomy/type/cognitive filters |
| `BLUEPRINT_SLOTS.*` | fixed-selection metadata | Có điều kiện | V2 approved đã chọn `QUESTION_ID` cố định |
| `EXAMS/EXAM_ITEMS` | import reference, không thay runtime snapshot | Tùy chọn | hiện rỗng; runtime dùng model GeneratedExam riêng |
| `USAGE_LOG` | usage import/export bridge | Tùy chọn | hiện rỗng; không tự ghi ngược master |

Mọi dòng source được giữ thêm trong `source_metadata` và hash canonical. `content_hash` phải
bao gồm câu, options/statements, taxonomy cần thiết, answer và metadata chấm; không bao gồm
thời điểm sync.

## 5. Miền giá trị và số liệu kiểm chứng

- 620 câu: 495 `MCQ_SINGLE`, 114 `TRUE_FALSE_GROUP`, 11 `SHORT_ANSWER`.
- Mức nhận thức: 270 `BIET`, 299 `HIEU`, 51 `VANDUNG`.
- Trạng thái: 615 `ACTIVE`, 5 `ARCHIVED`; process cached: 585
  `READY_FOR_PRACTICE`, 30 `READY_FOR_GRADUATION`, 5 `RETIRED`.
- Độ khó cached: mức 1/2/3/4/5 lần lượt 266/202/113/30/9.
- Mục đích cached: 589 `PRACTICE`, 26 `GRADUATION`, 5 `NONE`. Có chênh lệch 4 câu
  giữa purpose và process graduation; eligibility phải dùng `PROCESS_STATUS` theo
  `AUTO_USE_RULE`, không suy từ `USE_PURPOSE`.
- 1.980 options tạo đúng bốn label A–D cho 495 MCQ. Boolean tồn tại cả kiểu Boolean và
  chuỗi `TRUE/FALSE`, cần normalize.
- 456 statements tạo bốn label a–d cho 114 nhóm đúng/sai.
- `ANSWER_KEY` có cả nhãn A–D, chuỗi Đ/S và đáp án văn bản cho short answer; không thể
  ép toàn bộ về một scalar enum.
- `SCORE_RULES.QUESTION_TYPE` dùng tên legacy `TN_4_LUA_CHON/DUNG_SAI`, trong khi
  `QUESTIONS` dùng canonical `MCQ_SINGLE/TRUE_FALSE_GROUP`. Phải áp dụng
  `LEGACY_QUESTION_TYPE_MAP` từ `QUY_UOC`.
- Có 4 blueprint, trong đó hai V2 `APPROVED` (CS/ICT), tổng 28 nhóm câu, 10 điểm, 50 phút;
  không hard-code các con số này.
- `EXAMS`, `EXAM_ITEMS`, `USAGE_LOG`, `EXPORT_TEMPLATES` hiện chỉ có schema, chưa có dòng.

## 6. Điều kiện được đồng bộ và được chọn

Một câu được **đồng bộ projection** khi: khóa duy nhất; type/stem/version hợp lệ; answer
hợp lệ theo type; đủ options/statements tương ứng; liên kết curriculum/outcome/source tồn
tại; cached formula fields hợp lệ. Câu lỗi vẫn xuất hiện trong dry-run nhưng không được
apply một phần nếu lỗi nghiêm trọng.

Đồng bộ không đồng nghĩa được chọn vào đề:

- Luyện tập tự động: `QUESTIONS.PROCESS_STATUS=READY_FOR_PRACTICE`.
- Định kỳ: áp dụng nguyên văn `PERIODIC_ELIGIBILITY_RULE` trong `QUY_UOC`, gồm teaching
  plan/item approved, `ALLOWED_FOR_TESTING=TRUE`, điều kiện completed hoặc temporary mode,
  câu `READY_FOR_PERIODIC`, blueprint `APPROVED`.
- Tốt nghiệp: policy và blueprint đều `APPROVED`, câu
  `PROCESS_STATUS=READY_FOR_GRADUATION`.
- `RETIRED/ARCHIVED/NONE/NEEDS_REVIEW` không được chọn cho đề mới.
- Mỗi đề tối đa một câu trong cùng `FAMILY_ID`; duplicate decision `MERGE` phải được báo
  trong validation.
- Blueprint fixed selection chỉ dùng khi version approved và mọi slot/câu còn hợp lệ.

## 7. Trường chưa rõ và bất thường phải giải quyết

1. `EXPLANATION_ID` rỗng toàn bộ và không có sheet lời giải; hiện chưa có nguồn lời giải có
   cấu trúc để đồng bộ.
2. Tác giả câu/người kiểm duyệt không có cột riêng trong `QUESTIONS`; một phần nằm trong
   `NOTE`, `DUPLICATES.REVIEWED_BY` và `AUDIT_LOG`. Không được suy diễn tác giả từ actor.
3. Asset trực tiếp trong stem không có bảng riêng; chỉ có `QUESTION_SOURCES` → `FILES`.
   Cần xác nhận quy tắc nhận diện ảnh/bảng/mã nguồn nhúng trước Giai đoạn 2.
4. `DIFFICULTY`, `COMPETENCY`, `USE_PURPOSE`, `SHUFFLE_ALLOWED`, `FAMILY_ID`,
   `PROCESS_STATUS`, `CLASSIFICATION_BASIS` là công thức/cached value; XLSX parser thuần
   không tính được Google functions.
5. `TEACHING_PLAN_ITEMS` có 999 dòng không rỗng theo openpyxl do 819 dòng chứa cached
   `False` ở `ALLOWED_FOR_TESTING`, nhưng chỉ 180 dòng có `PLAN_ITEM_ID`. Importer phải
   xác định dòng nghiệp vụ bằng khóa chính, không bằng `any(cell)`.
6. `BLUEPRINT_CELLS.DIFFICULTY` hiện rỗng; generator không được giả định filter độ khó.
7. Chưa có dữ liệu EXAMS/usage thực để kiểm chứng semantics của snapshot/usage export.

## 8. Vòng đời projection

- Hash không đổi: cập nhật `last_synced_at`, không tạo revision.
- Hash đổi: tạo `BankQuestionRevision`; không ghi đè revision/snapshot cũ.
- Biến mất, archived hoặc retired: giữ vật lý và đánh dấu unavailable.
- Khôi phục trong master: có thể available trở lại sau validation và audit.
- Đề phát hành luôn giữ snapshot nội dung, thứ tự, protected answer, asset, blueprint và
  scoring version; sync sau đó không thay đổi đề/bài/điểm cũ.
- DMOJ không cung cấp màn hình sửa nội dung projection; mọi sửa nội dung diễn ra ở master.

## 9. Xác nhận cần có trước migration

Chủ sở hữu cần xác nhận: (a) dùng cached values hay Sheets API values làm giá trị chính
thức; (b) nguồn lời giải/asset nhúng; (c) semantics chính xác của 11 short-answer keys;
(d) công thức eligibility temporary teaching-plan mode; và (e) mapping legacy score types.
Sau xác nhận này mới chốt field/constraint và bắt đầu Giai đoạn 2 trong commit riêng.
