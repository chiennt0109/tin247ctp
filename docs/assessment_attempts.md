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

Grading backend và result release được mô tả riêng trong `docs/assessment_scoring.md`; tiến trình
RQ có thể quét các attempt hết hạn không còn request từ trình duyệt.

## Quyền và số lượt riêng — Giai đoạn 7

Khi kỳ thi dùng chế độ **Cấp quyền theo người dùng / nhóm**, mỗi `ExamAccessGrant` chọn đúng
một user hoặc một group. Grant có thể giới hạn theo số lượt, theo khoảng thời gian hiệu lực,
hoặc đồng thời cả hai. Grant trực tiếp của user được ưu tiên hơn grant của group; nếu user thuộc
nhiều group thì hệ thống dùng grant group đang có hiệu lực đầu tiên. Giới hạn này thay thế
`ExamSession.max_attempts` cho user tương ứng.

Grant riêng luôn được ưu tiên nếu tồn tại, kể cả với kỳ thi cũ vẫn đang lưu access mode mặc
định. Vì vậy `ExamSession.max_attempts` không thể chặn một user đã được cấp số lượt riêng.

Backend kiểm tra grant trong cùng transaction trước khi sinh đề. Với grant theo thời gian,
deadline của attempt là thời điểm sớm nhất giữa thời lượng bài, thời điểm đóng kỳ thi và thời
điểm grant hết hiệu lực. Grant không hợp lệ/hết hạn hoặc hết lượt không tạo `GeneratedExam`,
không tạo `ExamAttempt` và không tính lượt.

Với kỳ thi dùng nhóm ma trận tương đương, backend kiểm tra READY trực tiếp trước mỗi lần bắt
đầu và chọn bằng `secrets.choice`. Trong các lượt của cùng một user, hệ thống ưu tiên ma trận
READY chưa được user đó sử dụng; chỉ lặp lại sau khi đã đi hết các ma trận READY trong nhóm.
