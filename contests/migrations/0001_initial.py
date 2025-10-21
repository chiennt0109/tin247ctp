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
            name='Contest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('start_time', models.DateTimeField()),
                ('end_time', models.DateTimeField()),
                ('is_public', models.BooleanField(default=True)),
                ('problems', models.ManyToManyField(to='problems.problem')),
            ],
        ),
        migrations.CreateModel(
            name='Participation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.FloatField(default=0)),
                ('penalty', models.IntegerField(default=0)),
                ('last_submit', models.DateTimeField(blank=True, null=True)),
                ('contest', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='contests.contest')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.user')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='participation',
            unique_together={("contest", "user")},
        ),
    ]
