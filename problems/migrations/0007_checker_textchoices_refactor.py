from django.db import migrations, models


def normalize_checker_values(apps, schema_editor):
    Problem = apps.get_model("problems", "Problem")
    valid = {
        "none",
        "custom",
        "euler_path",
        "permutation",
        "matching",
        "graph_path",
        "grid",
        "set_compare",
        "float_tolerance",
        "permutation_constraints",
        "assignment",
        "constructive",
        "numeric_tolerance",
        "",
        None,
    }
    for p in Problem.objects.all().only("id", "checker"):
        v = p.checker
        if v in ("", None):
            p.checker = "none"
            p.save(update_fields=["checker"])
        elif v == "numeric_tolerance":
            p.checker = "float_tolerance"
            p.save(update_fields=["checker"])
        elif v not in valid:
            p.checker = "none"
            p.save(update_fields=["checker"])


class Migration(migrations.Migration):

    dependencies = [
        ("problems", "0006_problem_checker_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="problem",
            old_name="checker_type",
            new_name="checker",
        ),
        migrations.AlterField(
            model_name="problem",
            name="checker",
            field=models.CharField(
                choices=[
                    ("none", "None"),
                    ("custom", "Custom Checker"),
                    ("euler_path", "Euler Path"),
                    ("permutation", "Permutation"),
                    ("matching", "Matching"),
                    ("graph_path", "Graph Path"),
                    ("grid", "Grid Construction"),
                    ("set_compare", "Set Compare"),
                    ("float_tolerance", "Numeric Tolerance"),
                    ("permutation_constraints", "Permutation With Constraints"),
                    ("assignment", "Assignment"),
                    ("constructive", "Constructive"),
                ],
                default="none",
                max_length=50,
            ),
        ),
        migrations.RunPython(normalize_checker_values, migrations.RunPython.noop),
    ]
