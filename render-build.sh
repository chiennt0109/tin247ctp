#!/usr/bin/env bash
set -o errexit  # Dừng nếu có lỗi

# Cài thư viện cần thiết
pip install --upgrade pip
pip install -r requirements.txt

# Thu thập static files
python manage.py collectstatic --noinput

# Chạy migrate database
python manage.py migrate --noinput

# Chạy server gunicorn
gunicorn oj.wsgi:application
