from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("problems", "0005_alter_problemeditorial_access_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="problem",
            name="checker_config",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="problem",
            name="checker_file",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="problem",
            name="checker_type",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("euler_path", "Euler Path"),
                    ("graph_path", "Graph Path"),
                    ("permutation", "Permutation"),
                    ("permutation_constraints", "Permutation With Constraints"),
                    ("matching", "Matching"),
                    ("assignment", "Assignment"),
                    ("constructive", "Constructive"),
                    ("grid", "Grid"),
                    ("set_compare", "Set Compare"),
                    ("numeric_tolerance", "Numeric Tolerance"),
                    ("custom", "Custom Checker"),
                ],
                default="none",
                max_length=40,
            ),
        ),
    ]
