from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('arena', '0003_remove_arenagame_min_level_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='arenaprogress',
            name='current_x',
            field=models.IntegerField(default=5),
        ),
        migrations.AddField(
            model_name='arenaprogress',
            name='current_y',
            field=models.IntegerField(default=5),
        ),
    ]
