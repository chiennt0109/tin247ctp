from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        ('problems', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language', models.CharField(
                    max_length=10,
                    choices=[('cpp','C++'),('python','Python'),('pypy','PyPy'),('java','Java')]
                )),
                ('source_code', models.TextField()),
                ('verdict', models.CharField(default='Pending', max_length=50)),
                ('exec_time', models.FloatField(default=0.0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),

                # ✅ Không tạo lại các trường đã tồn tại trong DB
                ('passed_tests', models.IntegerField(default=0)),
                ('total_tests', models.IntegerField(default=0)),
                ('debug_info', models.TextField(blank=True, null=True)),

                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='problems.problem')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
        ),
    ]
