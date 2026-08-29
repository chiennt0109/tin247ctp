from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from problems.models import Problem

from . import admin as contests_admin
from .models import Contest, ContestProblemOrder


class ContestAdminProblemSelectorTests(TestCase):
    def test_admin_url_path_helper_is_imported(self):
        self.assertTrue(callable(contests_admin.path))

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="contest-admin",
            email="contest-admin@example.com",
            password="password",
        )
        cls.problem = Problem.objects.create(
            code="SEARCH01",
            title="Bài tìm kiếm nhanh",
            statement="Statement",
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_problem_field_uses_two_panel_filter_widget(self):
        response = self.client.get(reverse("admin:contests_contest_add"))
        field = response.context["adminform"].form.fields["problems"]
        widget = field.widget.widget

        self.assertEqual(widget.__class__.__name__, "FilteredSelectMultiple")
        self.assertFalse(widget.is_stacked)
        self.assertIn("mã hoặc tên bài", field.help_text)

    def test_add_page_exposes_searchable_problem_code_and_title(self):
        response = self.client.get(reverse("admin:contests_contest_add"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="selectfilter"')
        self.assertContains(response, 'data-is-stacked="0"')
        self.assertContains(response, "/static/admin/js/SelectFilter2.js")
        self.assertContains(response, "SEARCH01 - Bài tìm kiếm nhanh")

    def test_allowed_users_field_uses_two_panel_filter_widget(self):
        response = self.client.get(reverse("admin:contests_contest_add"))
        field = response.context["adminform"].form.fields["allowed_users"]
        widget = field.widget.widget

        self.assertEqual(widget.__class__.__name__, "FilteredSelectMultiple")
        self.assertFalse(widget.is_stacked)
        self.assertIn("Để trống", field.help_text)

    def test_chosen_problem_order_is_saved_for_contest_display(self):
        second_problem = Problem.objects.create(
            code="AAA-FIRST-BY-CODE",
            title="Second chosen",
            statement="Statement",
        )
        now = timezone.now()
        contest = Contest.objects.create(
            name="Ordered contest",
            start_time=now,
            end_time=now + timedelta(hours=1),
        )

        response = self.client.post(
            reverse("admin:contests_contest_change", args=[contest.pk]),
            {
                "name": contest.name,
                "description": "",
                "start_time_0": now.date().isoformat(),
                "start_time_1": now.time().strftime("%H:%M:%S"),
                "end_time_0": (now + timedelta(hours=1)).date().isoformat(),
                "end_time_1": (now + timedelta(hours=1)).time().strftime("%H:%M:%S"),
                "problems": [str(self.problem.pk), str(second_problem.pk)],
                "is_public": "on",
                "practice_time": "10800",
                "practice_open": "on",
                "_save": "Save",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            list(
                ContestProblemOrder.objects.filter(contest=contest).values_list(
                    "problem_id", flat=True
                )
            ),
            [self.problem.pk, second_problem.pk],
        )
        self.assertEqual(
            [problem.pk for problem in contest.ordered_problems()],
            [self.problem.pk, second_problem.pk],
        )
