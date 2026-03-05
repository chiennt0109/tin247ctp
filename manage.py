#!/usr/bin/env python
import os
import sys

def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "oj.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)

    # === AUTO CREATE ADMIN USER ===
    try:
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        User = get_user_model()

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "admin123")
            print("✅ Admin user created: admin / admin123")
        else:
            print("ℹ️ Admin user already exists")

    except Exception as e:
        print("⚠️ Auto-create admin failed:", e)

if __name__ == "__main__":
    main()
