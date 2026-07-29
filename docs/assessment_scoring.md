# Ma trận và quy tắc chấm điểm Assessment — Giai đoạn 3

## Mô hình phiên bản

`ExamBlueprint` là danh tính ma trận; `BlueprintVersion` giữ thời lượng, tổng câu, tổng điểm,
snapshot nguồn và báo cáo validation. Mỗi version có nhiều `BlueprintSection`, mỗi section
có các `BlueprintSlot`. Slot chứa taxonomy, loại câu, mức nhận thức, độ khó, năng lực, số
lượng, điểm, tag, điều kiện tốt nghiệp và chính sách tái sử dụng. Không có số câu hay công
thức tốt nghiệp hard-code trong model/validator.

`ScoringScheme` là danh tính bộ quy tắc; `ScoringSchemeVersion` giữ tổng điểm, số chữ số làm
tròn và snapshot policy nguồn. `ScoringRule.configuration` là JSON backend cho từng loại câu
và unique theo `(version, question_type)`. Giai đoạn grading sẽ diễn giải configuration từ
snapshot thay vì JavaScript/template.

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
