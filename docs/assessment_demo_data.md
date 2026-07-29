# Dữ liệu mẫu Assessment

## Nguồn

Command đọc workbook bằng chính `WorkbookBankImporter`, đồng thời chỉ chọn nội dung từ
`BankQuestion` đã đồng bộ; không tạo hoặc sửa câu hỏi. Bản master kiểm tra có 620 câu, 4
`BLUEPRINTS`, 100 `BLUEPRINT_CELLS`, 112 `BLUEPRINT_SLOTS`, 4 `SCORE_RULES`, một `EXAMS`
và 28 `EXAM_ITEMS`. Blueprint tốt nghiệp demo ưu tiên blueprint `APPROVED` và cell tương
ứng. Practice/periodic được suy ra tối thiểu từ taxonomy, type, cognitive level, difficulty
và process status thực trong projection; command ghi warning cho cấu hình suy ra.

## Cách chạy

```bash
python manage.py seed_assessment_demo --dry-run
python manage.py seed_assessment_demo --apply --student demo_student --teacher admin
python manage.py seed_assessment_demo --reset --student demo_student --teacher admin
```

Có thể dùng `--source=/secure/master.xlsx`. Hãy sync master và chạy dry-run trước. Không chạy
`--apply` tự động trong deploy production. `--with-sample-attempts` chủ động bị từ chối cho
đến khi Phase 5 có attempt/grading service, vì command không được ghi điểm giả trực tiếp.

## Dữ liệu được tạo

- ba blueprint/scoring scheme có `is_demo=True`, `demo_key` ổn định và tên `[DEMO]`;
- bốn session có slug ổn định: practice, periodic, graduation và access;
- một mã practice, bốn mã periodic, tối đa bốn mã graduation và một mã access;
- participant chỉ khi `--student` trỏ tới user hiện hữu;
- generated exam luôn đi qua `publish_exam_session()`/`ExamGenerator`, có seed/hash/snapshot.

Slot có `required_process_status`, do đó periodic không thể lấy câu practice-only và
graduation bắt buộc `READY_FOR_GRADUATION`. Nếu target không đạt hoặc validator lỗi, session
giữ `DRAFT` và không sinh đề. Scoring rule ưu tiên `SCORE_RULES`; loại câu không có rule
master nhận weight demo tối thiểu kèm warning, không được coi là công thức chính thức.

## Idempotency và reset

Apply dùng `get_or_create` theo `demo_key`/slug, không thêm version, session hoặc mã đề khi
chạy lại. Reset đếm rồi xóa theo thứ tự asset snapshot → question snapshot → generated exam
→ participant → session → blueprint/scoring children → demo roots. Bộ lọc `is_demo=True`
bảo vệ kỳ thi thật. Reset không chạm `BankQuestion`, revision, sync log hay user, sau đó tạo
lại demo trong cùng command.
