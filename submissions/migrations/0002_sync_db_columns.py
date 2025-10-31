from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('submissions', '0001_initial'),
    ]

    operations = [
        # --- Khai báo fields để Django biết và ghi nhận (không tạo lại nếu đã có) ---
        migrations.AddField(
            model_name='submission',
            name='passed_tests',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='submission',
            name='total_tests',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='submission',
            name='debug_info',
            field=models.TextField(blank=True, null=True),
        ),

        # --- Chỉ thêm cột nếu chưa tồn tại (PostgreSQL) ---
        migrations.RunSQL(
            sql="""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name='submissions_submission'
                    AND column_name='passed_tests'
                ) THEN
                    ALTER TABLE submissions_submission ADD COLUMN passed_tests integer DEFAULT 0;
                END IF;
                
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name='submissions_submission'
                    AND column_name='total_tests'
                ) THEN
                    ALTER TABLE submissions_submission ADD COLUMN total_tests integer DEFAULT 0;
                END IF;

                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name='submissions_submission'
                    AND column_name='debug_info'
                ) THEN
                    ALTER TABLE submissions_submission ADD COLUMN debug_info text;
                END IF;
            END $$;
            """,
            reverse_sql="""
            ALTER TABLE submissions_submission DROP COLUMN IF EXISTS passed_tests;
            ALTER TABLE submissions_submission DROP COLUMN IF EXISTS total_tests;
            ALTER TABLE submissions_submission DROP COLUMN IF EXISTS debug_info;
            """
        ),
    ]
