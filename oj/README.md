# DMOJ-Lite (Render Starter)

Django 5 + Gunicorn, chạy được trên Render (Free).  
Bước tiếp theo sẽ thêm DMOJ + worker chấm bài.

## Local
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

## 7) `manage.py`
```python
#!/usr/bin/env python
import os, sys

def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

if __name__ == "__main__":
    main()
