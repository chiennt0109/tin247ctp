# Ma trận, chấm điểm và công bố kết quả Assessment

## Mô hình phiên bản

`ExamBlueprint` là danh tính ma trận; `BlueprintVersion` giữ thời lượng, tổng câu, tổng điểm,
snapshot nguồn và báo cáo validation. Mỗi version có nhiều `BlueprintSection`, mỗi section
có các `BlueprintSlot`. Slot chứa taxonomy, loại câu, mức nhận thức, độ khó, năng lực, số
lượng, điểm, tag, điều kiện tốt nghiệp và chính sách tái sử dụng. Không có số câu hay công
thức tốt nghiệp hard-code trong model/validator.

`ScoringScheme` là danh tính bộ quy tắc; `ScoringSchemeVersion` giữ tổng điểm, số chữ số làm
tròn và snapshot policy nguồn. `ScoringRule.configuration` là JSON backend cho từng loại câu
và unique theo `(version, question_type)`. Backend diễn giải configuration từ snapshot;
template và JavaScript không chứa công thức hoặc đáp án đúng.

## Chấm bài — Giai đoạn 6

Khi nộp, `grade_attempt()` khóa bài làm, đọc `GeneratedExamQuestion` và
`ScoringSchemeVersion` đã snapshot, chuẩn hóa câu trả lời rồi chấm hoàn toàn ở backend.
Hiện bộ chấm hỗ trợ `MCQ_SINGLE`, `TRUE_FALSE_GROUP` và `SHORT_ANSWER`; điểm từng câu bị
chặn trong khoảng `0..score` của snapshot và tổng điểm được làm tròn theo
`rounding_digits`. Nếu thiếu rule hoặc gặp loại chưa hỗ trợ, service từ chối chấm thay vì
âm thầm cho điểm.

`GradingResult` lưu chi tiết giải thích theo câu, số đúng/sai/bỏ trống, rule code, tổng điểm
và phiên bản quy tắc. Chấm lại tạo sequence mới, đánh dấu kết quả cũ không còn current và
không xóa lịch sử. `ExamAttempt.score`, `graded_at` chỉ là bản tóm tắt của kết quả current.

Điểm và kết quả từng câu được công bố độc lập qua `score_release_mode` và
`answer_release_mode`. Các chế độ `NEVER`, ngay sau nộp, sau hết lượt, sau khi đóng, tại
thời điểm cấu hình và công bố thủ công đều được kiểm tra ở backend. Trang kết quả không
giải mã hoặc gửi đáp án chuẩn xuống trình duyệt.

## Trang kết quả và phân tích

- Học sinh dùng `/assessment/results/` và `/assessment/results/<attempt_id>/`. Kết quả có
  điểm theo phần, chủ đề, YCCD, mức nhận thức, lịch sử các lần làm và đánh dấu lần được
  tính chính thức theo policy của kỳ kiểm tra.
- Giáo viên có quyền `view_results` dùng `/assessment/manage/exams/<id>/results/` để xem
  trạng thái tham gia, thống kê điểm, phân tích từng `QUESTION_ID`, lựa chọn phương án,
  độ khó thực nghiệm, độ phân hóa và cảnh báo chất lượng câu.
- Các nút công bố/thu hồi điểm, đáp án và lời giải đều là POST, kiểm tra permission phía
  server và ghi `AssessmentAuditLog`.

## Đồng bộ cấu hình thật, loại bỏ demo

`sync_exam_bank --apply` hiện đồng bộ cùng transaction cả câu hỏi lẫn `BLUEPRINTS`,
`BLUEPRINT_CELLS` và `SCORE_RULES` đã duyệt. Ma trận được nhận dạng bằng
`source_blueprint_id`, giữ nguyên khối 10/11/12, loại kỳ, taxonomy, YCCD, mức nhận thức,
số lượng và điểm từ master; không sinh cấu hình `[DEMO]` và không tự bù câu sai điều kiện.

Sau khi kiểm tra backup, quản trị viên có thể loại bỏ riêng dữ liệu demo cũ bằng
`python manage.py seed_assessment_demo --purge`. Lệnh chỉ lọc các object `is_demo=True`,
không xóa ngân hàng câu hỏi hoặc tài khoản. Không chạy lệnh này trước khi kiểm tra dữ liệu
production.

## Validation trước khi khóa

`BlueprintValidator` kiểm tra:

- tổng `quantity` bằng `expected_question_count`;
- tổng `quantity * score_per_item` bằng `expected_total_score`;
- inventory khả dụng theo taxonomy/type/cognitive/difficulty/competency;
- thi tốt nghiệp chỉ dùng `READY_FOR_GRADUATION`;
- sức chứa distinct family đủ để không chọn hai câu cùng nhóm trùng;
- mọi loại câu trong slot có scoring rule tương ứng.

Mỗi slot trả trạng thái `NONE`, `INSUFFICIENT`, `TIGHT` hoặc `SUFFICIENT`, số ứng viên và
sức chứa family. Version chỉ được khóa khi report hợp lệ. Sau khi khóa, admin và model từ
chối sửa version/section/slot; thay đổi phải dùng `clone_blueprint_version()` để tạo version
mới. Migration Giai đoạn 3 chỉ tạo bảng Assessment mới, không sửa bảng judge/submission.

## Giao diện admin hiện tại

Các model được đăng ký vào admin site DMOJ hiện hữu. Section dùng inline slot để thêm/sửa
dòng ma trận; scoring version dùng inline rule. Danh sách version có filter trạng thái khóa,
khối và loại kỳ thi. Đây là editor nền tảng; kéo-thả, compare và mô phỏng scoring nâng cao
sẽ được bổ sung trên custom admin view mà không thay đổi version đã khóa.
