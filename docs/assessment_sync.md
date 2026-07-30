# Đồng bộ ngân hàng Assessment — Giai đoạn 2

## Nguồn và cấu hình

Nguồn duy nhất là master Google Sheet đã ánh xạ trong
`docs/assessment_bank_mapping.md`. Cấu hình runtime dùng biến môi trường:

```text
QUESTION_BANK_SOURCE=/secure/path/master.xlsx
QUESTION_BANK_FILE_ID=1kyaIfu7NSA4PQ_b6UXb8rRqJYLCdsUNF3AA8_Cf1BbQ
QUESTION_BANK_SYNC_ENABLED=false
GOOGLE_APPLICATION_CREDENTIALS=/secure/path/read-only-service-account.json
```

Không commit credential hoặc workbook. `QUESTION_BANK_SOURCE` có thể là file `.xlsx` cục
bộ hay HTTPS export URL. `QUESTION_BANK_FILE_ID` tạo URL export Google Sheets khi không có
source rõ ràng. Apply bị khóa mặc định và chỉ mở khi `QUESTION_BANK_SYNC_ENABLED=true`.

## Lệnh vận hành

```bash
python manage.py sync_exam_bank --source=/secure/master.xlsx --dry-run
python manage.py sync_exam_bank --source=/secure/master.xlsx --apply
python manage.py sync_exam_bank --source=/secure/master.xlsx --question-id=Q_ID --dry-run
```

Hai mode là mutually exclusive. Remote source bắt buộc HTTPS, giới hạn 50 MiB và được lưu
trong temporary file ngoài static/public rồi xóa. Apply theo `transaction.atomic()` và bị
từ chối nếu có bất kỳ lỗi cấu trúc nghiêm trọng. Dry-run không ghi database.

## Parser và báo cáo

Parser đọc workbook hai lần: raw formula và cached values. Dòng dữ liệu chỉ được nhận khi
cột khóa đầu tiên có giá trị, tránh 819 dòng format/cached `False` trong
`TEACHING_PLAN_ITEMS`. Hash canonical bao gồm stem, answer, options/statements, taxonomy và
các thuộc tính chọn câu, nhưng không bao gồm thời điểm sync.

Báo cáo gồm câu mới, thay đổi, không đổi, ngừng sử dụng, số câu hợp lệ, lỗi cấu trúc,
warning, câu không đủ điều kiện định kỳ/tốt nghiệp và `issue_counts`. Lỗi chi tiết phân biệt
khóa trùng, thiếu đáp án, type/mức/độ khó sai, options/statements sai, thiếu taxonomy,
outcome sai, thiếu source/asset và thiếu cached result.

## Apply và vòng đời

Apply đồng bộ taxonomy, source files, câu và source asset; tạo revision mới chỉ khi
`content_hash` đổi. Câu biến mất khỏi nguồn chỉ bị `is_available=False`, không xóa. Revision
cũ dùng `PROTECT`; đề phát hành ở giai đoạn sau sẽ snapshot revision. `protected_answer`
không đăng ký trong admin detail và không được dùng trong student API.

Mỗi apply thành công tạo `QuestionSyncLog` và `AssessmentAuditLog`; report/audit không chứa
toàn bộ đáp án. Audit không cho sửa/xóa qua model/admin. Lỗi apply rollback toàn bộ.

## Kết quả dry-run snapshot master ban đầu ngày 2026-07-29

Parser nhận 608 câu hợp lệ và phát hiện 13 lỗi nghiêm trọng:

- một khóa `RAW_PENDING.RAW_ID=RAW_TNT_F0001_D20_MCQ_12` bị trùng;
- 12 câu thiếu liên kết trong `QUESTION_SOURCES`.

Vì master quy định khóa đầu tiên unique và provenance là bắt buộc, hệ thống **đúng chủ ý
không apply** bản nguồn này. Chủ sở hữu cần sửa master rồi chạy lại dry-run; không nới
validator hay nhập một phần để né lỗi nguồn. Bản export được kiểm tra lại sau đó đã sửa
nhóm lỗi provenance này; kết quả mới nhất được ghi ở mục kế tiếp.

## Kiểm tra lỗi `ESTIMATED_TIME_SEC` ngày 2026-07-29

File vận hành được kiểm tra trực tiếp tại
`assessment/data/INDEX_NGAN_HANG_DE_TIN_HOC_TOT_NGHIEP_MASTER.xlsx` (file được ignore,
không commit đáp án). `ESTIMATED_TIME_SEC` nằm trong sheet `QUESTIONS`, cột P (header thứ
16); `USE_PURPOSE` nằm ở cột Q (header thứ 17). Header thực tế của `QUESTIONS` có 21 cột,
đúng thứ tự đã ghi trong tài liệu mapping.

Nguồn lỗi không phải do cột `PRACTICE` hợp lệ bị dịch vị trí trong parser. Trong bản XLSX
được kiểm tra, 31 ô thuộc chính cột P/`ESTIMATED_TIME_SEC` chứa literal `PRACTICE`; cùng
hàng, cột Q/`USE_PURPOSE` cũng có cached value `PRACTICE`. Ví dụ đầu tiên là hàng 109,
`QUESTION_ID=Q_TNT_F0001_D03_020`: raw value cột P là literal `PRACTICE`, trong khi raw
value cột Q là công thức xác định purpose. Không sửa workbook trong repository để che lỗi
nguồn này.

Lỗi phần mềm là dry-run trước đây chỉ ép kiểu `DIFFICULTY` và boolean, còn
`ESTIMATED_TIME_SEC` được giữ raw rồi mới gọi `int()` trong apply. Vì vậy dry-run báo 620
câu hợp lệ nhưng apply mới crash. Parser mới chuẩn hóa header (Unicode/case/whitespace),
ánh xạ bằng tên header, parse/validate integer, decimal, boolean, enum và date/datetime
trước khi tạo `ParsedBank`. Apply chỉ dùng `estimated_time_seconds` đã chuẩn hóa, không ép
kiểu lại. Với bản file được kiểm tra, dry-run nay quét đủ 620 dòng câu hỏi, chỉ tính 589 câu
hợp lệ, trả 31 `INVALID_FIELD_TYPE` và chặn apply nguyên tử cho đến khi master được sửa tại
nguồn.

## Rollback

Migration `assessment/0001_initial` chỉ tạo bảng mới và rollback bằng migrate về zero khi
chưa có module phụ thuộc. Trước production phải backup PostgreSQL. Rollback code không được
xóa projection/revision đã có lịch sử đề; khi hệ thống đã phát hành đề phải dùng forward
migration và giữ dữ liệu audit/snapshot.
