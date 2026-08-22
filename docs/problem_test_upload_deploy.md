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
   sudo systemctl restart tin247ctp
   ```

   Dịch vụ systemd chạy Gunicorn cũng cần `--timeout 300`. Ví dụ dòng
   `ExecStart` phải chứa `gunicorn --timeout 300 --graceful-timeout 30 ...`;
   sau khi sửa unit, chạy `sudo systemctl daemon-reload` trước khi restart.

4. Xác nhận cấu hình nginx thực tế đã nhận giới hạn:

   ```bash
   sudo nginx -T | grep -n "client_max_body_size 260m"
   ```

Không đặt `client_max_body_size 0` vì sẽ loại bỏ lớp bảo vệ ở reverse proxy.
Nếu thay đổi giới hạn bằng biến môi trường Django, phải đồng bộ giới hạn nginx;
nginx nên bằng giới hạn file cộng khoảng 4 MiB multipart overhead, thay vì lớn
hơn tùy ý.
