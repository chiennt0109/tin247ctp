# Phase 5 — Làm bài, autosave và nộp bài

## Luồng học sinh

`POST /assessment/exams/<slug>/start/` tạo hoặc trả lại attempt đang làm, sau đó chuyển tới
`/assessment/attempts/<uuid>/`. Trang làm bài chỉ render snapshot nội dung công khai; answer key,
lời giải, source `QUESTION_ID` và metadata chấm không được đưa vào HTML/JavaScript.

Trang hỗ trợ danh sách câu, đánh dấu xem lại, trạng thái đã trả lời, đồng hồ dựa trên thời gian
server, cảnh báo mất mạng, localStorage tạm thời, autosave debounce và xác nhận trước khi nộp.

## API

- `PATCH /assessment/api/attempts/<uuid>/answers/`: batch upsert câu trả lời với `version`.
- `POST /assessment/api/attempts/<uuid>/submit/`: nộp idempotent, server quyết định hết giờ.
- `GET /assessment/api/attempts/<uuid>/state/`: trạng thái/version/thời gian server.

Autosave khóa row attempt trong transaction và dùng optimistic locking. Request version cũ trả
HTTP 409 cùng version hiện tại, không ghi đè dữ liệu mới. Câu hỏi không thuộc đúng generated exam
bị từ chối. Attempt hết giờ được server chuyển `AUTO_SUBMITTED`; sau submit không thể chỉnh sửa.

## Dữ liệu

`AttemptAnswer` unique theo `(attempt, exam_question)`, lưu JSON answer, cờ xem lại và thời điểm
lưu. `ExamAttempt.data_version` tăng sau mỗi batch thành công; `submitted_at` lấy từ server.
Migration `0008_attempt_answers_and_autosave` chỉ thêm bảng/field, không tác động ngân hàng.

Phase tiếp theo sẽ bổ sung grading backend từ scoring snapshot, result release và RQ sweep cho
attempt hết hạn không còn request từ trình duyệt.
