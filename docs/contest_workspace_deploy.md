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

Build hai image playground lần đầu (hoặc sau khi Dockerfile thay đổi):

```bash
cd /var/www/tin247ctp
sudo docker build -t judge-cpp -f docker/playground/cpp/Dockerfile .
sudo docker build -t judge-py -f docker/playground/python/Dockerfile .
python manage.py check_playground_runner
```

Nếu Gunicorn chạy bằng `www-data`, user đó phải truy cập được Docker socket. Sau
khi thêm group phải restart service để tiến trình nhận group mới:

```bash
sudo usermod -aG docker www-data
sudo systemctl restart tin247ctp
```

Nếu nút **Biên dịch và chạy** báo `JE`, kiểm tra Redis và Docker bằng tài khoản
đang chạy dịch vụ web (thay `www-data` nếu VPS dùng user khác):

```bash
sudo -u www-data docker image inspect judge-cpp judge-py
sudo -u www-data docker run --rm --network=none judge-cpp g++ --version
sudo -u www-data docker run --rm --network=none judge-py python3 --version
sudo journalctl -u tin247ctp -n 100 --no-pager
```

Ứng dụng dùng `CACHE_URL` nếu biến này tồn tại, nếu không sẽ dùng `REDIS_URL`.
Không đặt Redis production cố định thành `localhost` khi Redis chạy ở dịch vụ khác.

API mới là `POST /api/playground/run/` (yêu cầu session đăng nhập và CSRF):

```json
{"problem_code":"DRV_F0154","language":"cpp17","source":"...","stdin":"...","sample_id":""}
```

Có thể đổi tên image qua `PLAYGROUND_CPP_IMAGE` và `PLAYGROUND_PYTHON_IMAGE`.
Playground tách biệt với worker chấm chính thức; chỉ cần restart Gunicorn/web,
không bắt buộc restart nginx hay worker nếu worker không được cập nhật code khác.

Migration `problems.0009_testcase_is_sample` thêm cờ **Test ví dụ**. Test cũ mặc
định là test ẩn; quản trị viên có thể mở bài trong admin và đánh dấu những test
được phép công khai. Nên sao lưu cơ sở dữ liệu trước khi migrate trên production.

Tên virtualenv, thư mục dự án hoặc systemd service có thể khác giữa các VPS; thay
`/path/to/tin247ctp`, `.venv`, `tin247ctp` và `tin247ctp-rqworker` cho đúng cấu hình.
