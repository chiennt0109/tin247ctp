from django.apps import AppConfig
from django.db import connection

class SubmissionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'submissions'

    def ready(self):
        try:
            with connection.cursor() as cursor:
                # Lấy danh sách cột hiện tại
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name='submissions_submission';
                """)
                cols = [row[0] for row in cursor.fetchall()]

                # Ép thêm cột nếu thiếu
                if "passed_tests" not in cols:
                    cursor.execute("""
                        ALTER TABLE submissions_submission 
                        ADD COLUMN passed_tests integer DEFAULT 0;
                    """)

                if "total_tests" not in cols:
                    cursor.execute("""
                        ALTER TABLE submissions_submission 
                        ADD COLUMN total_tests integer DEFAULT 0;
                    """)

                if "debug_info" not in cols:
                    cursor.execute("""
                        ALTER TABLE submissions_submission 
                        ADD COLUMN debug_info text DEFAULT '';
                    """)

        except Exception as e:
            print("⚠️ Auto-migrate submissions table failed:", e)
