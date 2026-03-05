# path: problems/migrations/0002_auto_20251117_1448.py

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('problems', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [

        # ==========================================
        #   ONLY CREATE USERPROGRESS (DB CHƯA CÓ)
        # ==========================================
        migrations.CreateModel(
            name='UserProgress',
            fields=[
                ('id', models.BigAutoField(auto_created=True,
                                           primary_key=True,
                                           serialize=False,
                                           verbose_name='ID')),
                ('status', models.CharField(
                    max_length=20,
                    default="not_started",
                    choices=[
                        ("not_started", "Chưa bắt đầu"),
                        ("in_progress", "Đang làm"),
                        ("solved", "Đã AC")
                    ]
                )),
                ('attempts', models.PositiveIntegerField(default=0)),
                ('best_score', models.FloatField(default=0)),
                ('last_submit', models.DateTimeField(auto_now=True)),

                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='progress',
                    to=settings.AUTH_USER_MODEL
                )),

                ('problem', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='user_progress',
                    to='problems.problem'
                )),
            ],
            options={
                'unique_together': {('user', 'problem')},
            },
        ),

        migrations.AddIndex(
            model_name='userprogress',
            index=models.Index(fields=['user', 'status'], name='user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='userprogress',
            index=models.Index(fields=['problem'], name='problem_idx'),
        ),
    ]
