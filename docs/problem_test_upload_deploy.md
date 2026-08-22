# Deploy upload test lớn qua nginx

Lỗi `413 Request Entity Too Large` có chữ ký `nginx` được trả về **trước khi
request tới Django**. Vì vậy chỉ thay đổi `oj/settings.py` không thể xử lý lỗi
này; reverse proxy cũng phải được cấu hình.

## Các giới hạn đã chọn

| Lớp | Giới hạn | Mục đích |
|---|---:|---|
| nginx request | 260 MiB | 256 MiB ZIP + 4 MiB multipart overhead |
| File ZIP nén | 256 MiB | Chặn archive nén quá lớn tại Django |
| Django request | 1 GiB | Có khoảng trống cho multipart form |
| ZIP sau giải nén | 1 GiB | Đủ cho 40–50 test lớn nhưng vẫn chống ZIP bomb |
| Dung lượng đĩa dự phòng | 2 GiB | Không cho giải nén làm đầy filesystem |
| Số file trong ZIP | 2.000 | Chặn archive bất thường |

File upload trên 5 MiB được Django stream xuống file tạm thay vì giữ toàn bộ
trong RAM. Trước khi giải nén, ứng dụng kiểm tra kích thước khai báo của ZIP,
đường dẫn traversal/symlink và dung lượng đĩa còn trống.

## Áp dụng trên máy chủ Ubuntu/nginx

### Cách tự động (khuyến nghị)

Sau khi `git pull`, chạy đúng **một lệnh** sau từ thư mục repository:

```bash
sudo bash deploy/nginx/install-problem-test-upload.sh
```

Script cài giới hạn hữu hạn 260 MiB tại nginx `http` scope, chạy `nginx -t`,
tự hoàn tác nếu cấu hình lỗi, reload nginx và xác nhận cấu hình thực sự đang
hoạt động. Không cần biết tên systemd service của Django để sửa lỗi 413 nginx.

### Cách thủ công cho riêng virtual host

1. Mở file `server` HTTPS hiện tại của `tin247ctp.com` (thường nằm tại
   `/etc/nginx/sites-available/tin247ctp`).
2. Bên trong khối `server { ... }`, thêm:

   ```nginx
   include /var/www/tin247ctp/deploy/nginx/problem-test-upload.conf;
   ```

   Điều chỉnh `/var/www/tin247ctp` nếu repository được deploy ở đường dẫn khác.
3. Kiểm tra và reload an toàn:

   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

   **Không chạy** `systemctl restart tin247ctp` nếu unit đó không tồn tại.
   Việc reload nginx đã đủ để sửa lỗi 413. Có thể tìm đúng tên service bằng:

   ```bash
   systemctl list-units --type=service --all | grep -Ei 'tin247|gunicorn|daphne|uwsgi'
   ```

   Dịch vụ systemd chạy Gunicorn nên có `--timeout 300`. Ví dụ dòng
   `ExecStart` phải chứa `gunicorn --timeout 300 --graceful-timeout 30 ...`;
   chỉ sau khi sửa unit mới chạy `sudo systemctl daemon-reload` và restart
   **đúng tên unit vừa tìm được**.

4. Xác nhận cấu hình nginx thực tế đã nhận giới hạn:

   ```bash
   sudo nginx -T 2>&1 | grep -Fn -- "client_max_body_size 260m;"
   ```

Không dán nhiều lệnh có chuỗi ký tự `\n` trên cùng một dòng. Trong log ở trên,
`grep: invalid option -- 't'` xuất hiện vì lệnh `grep` và `sudo nginx -t` bị
nối liền; đó không phải kết quả xác nhận giới hạn đã hoạt động.

Không đặt `client_max_body_size 0` vì sẽ loại bỏ lớp bảo vệ ở reverse proxy.
Nếu thay đổi giới hạn bằng biến môi trường Django, phải đồng bộ giới hạn nginx;
nginx nên bằng giới hạn file cộng khoảng 4 MiB multipart overhead, thay vì lớn
hơn tùy ý.
