# Audit và refactor Phase 4 on-demand

## Kết quả audit trước thay đổi

### Giữ nguyên

- Toàn bộ projection ngân hàng, revision, asset, sync/audit log.
- Blueprint/section/slot/version và scoring scheme/rule/version.
- `ExamSession` với vai trò cấu hình; `ExamParticipant` với vai trò quyền/override.
- Snapshot `GeneratedExamQuestion`/asset và mã hóa đáp án.

### Refactor

- `GeneratedExam` có purpose bắt buộc `ATTEMPT` hoặc `PREVIEW`.
- `ExamSession.generation_mode` chuyển sang ba mode on-demand/fixed và có access mode.
- Publish chỉ khóa/mở cấu hình, không sinh đề.
- Student list dựa trên access policy, không dựa trên assignment.
- Demo seed chỉ dựng cấu hình và quyền, không pre-generate.

### Legacy đã loại bỏ

- `generate_codes()` và `generate_for_user()` dùng để sinh trước/phân phối đề.
- Hành vi sinh `GeneratedExam` trong `publish_exam_session()` và demo seed.
- Unique `(session, code)` vốn giả định pool đề sinh sẵn.
- Không có model assignment riêng trong schema cũ, vì vậy không có model/field assignment cần drop.

## Dữ liệu legacy và migration

Migration `0007_on_demand_attempts` nối tiếp `0006`, tạo attempt/access fields/constraints,
chuyển ba generation mode cũ và phân loại tất cả đề pre-generated (thời điểm schema chưa có
attempt) thành preview đã hết hạn. Không xóa ngân hàng, user, blueprint hoặc scoring.

Việc xóa được tách khỏi migration để operator xem trước:

```bash
python manage.py cleanup_assessment_phase4_legacy --dry-run
python manage.py cleanup_assessment_phase4_legacy --apply  # chỉ sau khi duyệt dry-run
```

Cleanup xóa preview hết hạn và ATTEMPT exam không có attempt; FK cascade dọn question/asset.
Attempt `IN_PROGRESS` thiếu đề được chuyển `INVALIDATED` để không còn invariant hỏng.

## Trình tự VPS

1. Backup PostgreSQL.
2. Deploy code và dừng worker ghi assessment.
3. Chạy cleanup `--dry-run` trước migration. Command tự nhận diện `PRE_0007_READ_ONLY`, chỉ
   đếm trực tiếp các bảng legacy và tuyệt đối không join bảng attempt chưa tồn tại.
4. Chạy `python manage.py migrate --plan` và kiểm tra chỉ migration dự kiến.
5. Chạy `python manage.py migrate` (không được agent chạy tự động trên production). Bước này
   chỉ phân loại pre-generated exam thành preview hết hạn, chưa xóa chúng.
6. Chạy cleanup `--dry-run` lần hai trên schema mới, lưu và duyệt báo cáo chi tiết.
7. Sau phê duyệt riêng, chạy cleanup `--apply`.
8. Chạy lại cleanup `--dry-run`, xác nhận orphan/broken/legacy đều bằng 0.
9. Chạy `python manage.py check` và smoke test Start bằng tài khoản thử.
