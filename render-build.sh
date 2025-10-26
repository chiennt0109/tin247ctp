#!/usr/bin/env bash
# =====================================
# 🚀 Render Build Script (Stable v1.2)
# Mục tiêu: Tự động cài đặt, migrate, thu thập static và sẵn sàng chạy Gunicorn
# =====================================

# ❌ Dừng ngay nếu có lỗi
set -o errexit

echo "📦 Bắt đầu cài đặt môi trường Python..."

# ⚙️ Đảm bảo pip mới nhất
pip install --upgrade pip

# 🧩 Cài đặt tất cả dependency từ requirements.txt
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  echo "❗Không tìm thấy requirements.txt — kiểm tra lại repository."
  exit 1
fi

echo "✅ Cài đặt hoàn tất, bắt đầu migrate database..."

# 🗄️ Chạy migrate database
python manage.py migrate --noinput

echo "✅ Migrate thành công, thu thập static files..."

# 🎨 Thu thập static files
python manage.py collectstatic --noinput

echo "✅ Hoàn tất collectstatic."
echo "🚀 Sẵn sàng khởi chạy Gunicorn (qua Procfile)."
