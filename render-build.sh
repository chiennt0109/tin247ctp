# path: render-build.sh
#!/usr/bin/env bash
set -o errexit

# Thu thập static
python manage.py collectstatic --noinput

# Chạy migrate database
python manage.py migrate --noinput

# Khởi động gunicorn
gunicorn oj.wsgi:application
