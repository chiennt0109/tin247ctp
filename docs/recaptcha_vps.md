# Cấu hình reCAPTCHA trên VPS

Trang đăng ký dùng **Google reCAPTCHA v2 Checkbox**. Site key là dữ liệu công
khai, nhưng secret key chỉ được lưu trong biến môi trường hoặc file `.env` trên
VPS và không được đưa vào Git.

## Cấu hình

```bash
cd /duong-dan/toi/tin247ctp
cp -n .env.example .env
chmod 600 .env
```

Điền `RECAPTCHA_PRIVATE_KEY` trong `.env`, sau đó kiểm tra mà không in secret:

```bash
python manage.py shell -c "from django.conf import settings; print('site_key=', settings.RECAPTCHA_PUBLIC_KEY); print('secret_configured=', bool(settings.RECAPTCHA_PRIVATE_KEY)); print('domain=', settings.RECAPTCHA_DOMAIN)"
```

Khởi động lại web service sau khi thay đổi `.env`:

```bash
sudo systemctl restart tin247ctp
sudo journalctl -u tin247ctp -n 100 --no-pager
```

Trong Google reCAPTCHA Admin Console, khóa phải có loại **Challenge (v2) / I'm
not a robot Checkbox** và danh sách domain phải chứa `tin247ctp.com` (không thêm
`https://` hoặc đường dẫn). Nếu khóa thuộc reCAPTCHA v3 hoặc domain chưa được
cho phép, widget sẽ báo lỗi dù giá trị key đã được cấu hình trên máy chủ.

Nếu VPS không truy cập được `google.com`, đặt biến sau rồi restart service:

```dotenv
RECAPTCHA_DOMAIN=www.recaptcha.net
```
