# Generated manually for Render (initial migration)
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Problem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=20, unique=True)),
                ('title', models.CharField(max_length=100)),
                ('statement', models.TextField()),
                ('input_spec', models.TextField(blank=True)),
                ('output_spec', models.TextField(blank=True)),
                ('sample_input', models.TextField(blank=True)),
                ('sample_output', models.TextField(blank=True)),
                ('time_limit', models.FloatField(default=1.0)),
                ('memory_limit', models.IntegerField(default=256)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Submission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username', models.CharField(max_length=50)),
                ('language', models.CharField(max_length=20)),
                ('code', models.TextField()),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(default='Pending', max_length=20)),
                ('result', models.TextField(blank=True)),
                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='judge.problem')),
            ],
        ),
    ]
