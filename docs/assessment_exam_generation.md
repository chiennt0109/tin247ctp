# Kỳ kiểm tra và sinh đề on-demand — Giai đoạn 4

## Kiến trúc được giữ

`ExamSession` là cấu hình sinh đề, không phải một đề được phân phối sẵn. Session tham chiếu
phiên bản blueprint/scoring đã khóa, cửa sổ thời gian, số lượt, chính sách công bố, chế độ
truy cập và một trong ba chế độ sinh:

- `ON_DEMAND_INDIVIDUAL` (mặc định): mỗi lần bắt đầu sinh một snapshot riêng;
- `ON_DEMAND_CODE_POOL`: chọn mã trong pool khi bắt đầu nhưng vẫn snapshot riêng cho attempt;
- `FIXED_EXAM`: dùng seed cố định theo session, nhưng không pre-assign học sinh.

`ExamParticipant` chỉ là override/whitelist/blacklist quyền, thời gian, số lượt và download.
Nó không chứa đề, mã đề hay assignment. `ALL_USERS` không yêu cầu admin thêm từng học sinh;
các mode còn lại là `SELECTED_GROUPS`, `SELECTED_GRADES`, `SELECTED_USERS`.

## Điểm tạo đề duy nhất

`assessment.services.start_attempt.start_attempt(user, session)` giữ Redis lock theo
`assessment:start:<session_id>:<user_id>`, sau đó chạy transaction: khóa session, kiểm quyền,
trạng thái, cửa sổ, lượt và attempt đang mở; validate blueprint; reserve attempt; sinh snapshot;
gắn `GeneratedExam(purpose=ATTEMPT)` vào attempt và commit. Lỗi ở bất kỳ bước nào rollback cả
attempt lẫn snapshot. Double click/refresh trả lại attempt `IN_PROGRESS` hiện hữu.

Publish chỉ validate/khóa cấu hình và mở/lên lịch session; không sinh đề. Demo seed cũng không
sinh đề. Preview lưu DB phải dùng `purpose=PREVIEW` và `expires_at`; API preview không tạo attempt.

## Snapshot và an toàn

Generator lọc từng slot theo taxonomy, loại, mức nhận thức, độ khó, eligibility và process
status; không lặp câu hoặc duplicate family trong một đề. Thiếu pool làm toàn transaction thất
bại. Snapshot giữ stem/options/statements/assets và đáp án được mã hóa; trang debug học sinh chỉ
đọc nội dung công khai, không gửi answer key, lời giải, QUESTION_ID hay grading metadata.

## Dọn Phase 4 cũ

Chạy trước trên VPS:

```bash
python manage.py cleanup_assessment_phase4_legacy --dry-run
```

Sau khi duyệt báo cáo mới chạy `--apply`. Command xóa preview hết hạn và `ATTEMPT` exam không có
attempt, cascade snapshot con, đồng thời vô hiệu hóa attempt đang làm bị thiếu đề. Nó không xóa
ngân hàng, user, blueprint hay scoring. Migration `0007` chỉ phân loại đề pre-generated cũ thành
preview đã hết hạn để command có thể báo cáo/xóa có kiểm soát.
