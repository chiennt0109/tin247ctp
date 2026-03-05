#!/usr/bin/env bash
set -o errexit

# Cài dependencies
pip install -r requirements.txt

# Chạy migrate trước khi server start
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# Thu thập static files
python manage.py collectstatic --noinput

# (Render sẽ tự chạy gunicorn theo Procfile)
