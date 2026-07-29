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

## Kết quả dry-run master ngày 2026-07-29

Parser nhận 608 câu hợp lệ và phát hiện 13 lỗi nghiêm trọng:

- một khóa `RAW_PENDING.RAW_ID=RAW_TNT_F0001_D20_MCQ_12` bị trùng;
- 12 câu thiếu liên kết trong `QUESTION_SOURCES`.

Vì master quy định khóa đầu tiên unique và provenance là bắt buộc, hệ thống **đúng chủ ý
không apply** bản nguồn này. Chủ sở hữu cần sửa master rồi chạy lại dry-run; không nới
validator hay nhập một phần để né lỗi nguồn.

## Rollback

Migration `assessment/0001_initial` chỉ tạo bảng mới và rollback bằng migrate về zero khi
chưa có module phụ thuộc. Trước production phải backup PostgreSQL. Rollback code không được
xóa projection/revision đã có lịch sử đề; khi hệ thống đã phát hành đề phải dùng forward
migration và giữ dữ liệu audit/snapshot.
