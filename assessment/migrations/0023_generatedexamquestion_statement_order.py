from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("assessment", "0022_examaccessgrant_grant_source")]
    operations = [
        migrations.AlterField(
            model_name="examblueprint",
            name="status",
            field=models.CharField(
                choices=[("DRAFT", "Nháp"), ("REVIEW", "Đang rà soát"),
                         ("APPROVED", "Đã duyệt"), ("LOCKED", "Đã khóa")],
                db_index=True, default="DRAFT", max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="generatedexamquestion",
            name="statement_order",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
