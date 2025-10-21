#!/usr/bin/env bash
# --- Render build script for Django ---
set -o errexit  # dừng nếu có lỗi

echo "⚙️ Installing dependencies..."
pip install -r requirements.txt

echo "📦 Running migrations..."
python manage.py makemigrations --noinput || true
python manage.py migrate --noinput

echo "🎨 Collecting static files..."
python manage.py collectstatic --noinput || true

echo "✅ Build step finished."
