# Kỳ kiểm tra và sinh đề — Giai đoạn 4

## Kỳ kiểm tra

`ExamSession` liên kết trực tiếp phiên bản blueprint và scoring, có UUID/slug, loại kỳ thi,
thời gian mở/đóng, thời lượng, số lượt, cách chọn kết quả nhiều lần, khoảng chờ, đảo câu/
phương án, số mã đề, chế độ sinh, chính sách công bố điểm/đáp án và quyền tải/xem lại.
Validation không cho cửa sổ thời gian sai, cấu hình số mã trái generation mode hoặc thiếu
thời điểm cho chế độ công bố `AT_SPECIFIC_TIME`.

`ExamParticipant` liên kết `AUTH_USER_MODEL` và session, unique theo user/session, hỗ trợ
làm bù, làm sau hạn, thời gian cộng thêm, override số lượt và cửa sổ cá nhân.

## Sinh và snapshot đề

`ExamGenerator` chỉ chạy khi blueprint/scoring đã khóa. Với mỗi slot, service lọc projection
khả dụng theo taxonomy/type/mức/độ khó/năng lực và điều kiện tốt nghiệp, sau đó chọn theo
seed có thể tái tạo. Một câu và một duplicate family chỉ xuất hiện tối đa một lần trong đề.
Thiếu distinct candidate làm transaction thất bại toàn bộ.

`GeneratedExam` giữ code, seed, version, tổng điểm, validation report và SHA-256 toàn đề.
`GeneratedExamQuestion` giữ revision nguồn cùng snapshot stem/options/statements, thứ tự,
điểm và đáp án được mã hóa Fernet bằng khóa dẫn xuất phía server. `GeneratedExamAsset` snapshot ID, tên, MIME,
trang và checksum của asset; không phụ thuộc đường dẫn Drive khi học sinh mở đề.

Ba mode được hỗ trợ:

- `COMMON_EXAM`: sinh một mã;
- `MULTIPLE_EQUIVALENT_CODES`: sinh trước `code_count` mã bằng các derived seed;
- `INDIVIDUAL_EXAM`: không sinh trước; `generate_for_user()` dùng seed session/user.

## Phát hành

`publish_exam_session()` khóa row session, yêu cầu trạng thái draft, kiểm tổng scoring với
blueprint, chạy validation inventory/scoring, khóa hai version, sinh mã đề, khóa đề và chuyển
session sang scheduled/open theo giờ server. Toàn bộ chạy trong transaction và ghi audit cho
khóa blueprint, từng đề sinh và phát hành session. Đề đã snapshot không đổi khi bank revision
sau đó thay đổi.
