from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0001_initial'),
    ]

    operations = [
        # ✅ Báo cho Django là đã sync rồi, KHÔNG tạo lại các field
        migrations.RunSQL(
            sql="""
            ALTER TABLE submissions_submission
            ADD COLUMN IF NOT EXISTS passed_tests integer DEFAULT 0;
            ALTER TABLE submissions_submission
            ADD COLUMN IF NOT EXISTS total_tests integer DEFAULT 0;
            ALTER TABLE submissions_submission
            ADD COLUMN IF NOT EXISTS debug_info text;
            """,
            reverse_sql="""
            ALTER TABLE submissions_submission DROP COLUMN IF EXISTS passed_tests;
            ALTER TABLE submissions_submission DROP COLUMN IF EXISTS total_tests;
            ALTER TABLE submissions_submission DROP COLUMN IF EXISTS debug_info;
            """,
        ),
    ]
