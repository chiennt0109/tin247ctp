from django.db import migrations, models
import django.db.models.deletion


def initialize_problem_order(apps, schema_editor):
    Contest = apps.get_model("contests", "Contest")
    ContestProblemOrder = apps.get_model("contests", "ContestProblemOrder")
    for contest in Contest.objects.all().iterator():
        problem_ids = contest.problems.order_by("code").values_list("pk", flat=True)
        ContestProblemOrder.objects.bulk_create(
            ContestProblemOrder(
                contest_id=contest.pk,
                problem_id=problem_id,
                position=position,
            )
            for position, problem_id in enumerate(problem_ids, start=1)
        )


class Migration(migrations.Migration):
    dependencies = [("contests", "0007_contest_allowed_users")]

    operations = [
        migrations.CreateModel(
            name="ContestProblemOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveIntegerField()),
                ("contest", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="problem_display_orders", to="contests.contest")),
                ("problem", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="problems.problem")),
            ],
            options={"ordering": ("position",)},
        ),
        migrations.RunPython(initialize_problem_order, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="contestproblemorder",
            constraint=models.UniqueConstraint(fields=("contest", "problem"), name="unique_contest_problem_display_order"),
        ),
        migrations.AddConstraint(
            model_name="contestproblemorder",
            constraint=models.UniqueConstraint(fields=("contest", "position"), name="unique_contest_problem_position"),
        ),
    ]
