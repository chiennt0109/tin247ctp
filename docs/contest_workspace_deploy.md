# Cập nhật giao diện làm bài contest trên VPS

Sau khi upload/pull phiên bản code mới vào thư mục dự án, chạy:

```bash
cd /path/to/tin247ctp
source .venv/bin/activate
python manage.py migrate --plan
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart tin247ctp
sudo systemctl restart tin247ctp-rqworker
sudo systemctl --no-pager --full status tin247ctp tin247ctp-rqworker
```

Migration `problems.0009_testcase_is_sample` thêm cờ **Test ví dụ**. Test cũ mặc
định là test ẩn; quản trị viên có thể mở bài trong admin và đánh dấu những test
được phép công khai. Nên sao lưu cơ sở dữ liệu trước khi migrate trên production.

Tên virtualenv, thư mục dự án hoặc systemd service có thể khác giữa các VPS; thay
`/path/to/tin247ctp`, `.venv`, `tin247ctp` và `tin247ctp-rqworker` cho đúng cấu hình.
