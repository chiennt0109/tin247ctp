from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from contests.models import Contest, Participation, PracticeSession
from problems.models import Problem
from submissions.models import Submission


class ContestAdminProblemSelectorTests(TestCase):
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


class ContestAdminResetTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="reset-admin",
            email="reset-admin@example.com",
            password="password",
        )
        self.competitor = User.objects.create_user(username="competitor")
        self.problem = Problem.objects.create(
            code="RESET01", title="Bài giữ lại", statement="Statement"
        )
        now = timezone.now()
        self.contest = Contest.objects.create(
            name="Contest cần reset", start_time=now, end_time=now
        )
        self.contest.problems.add(self.problem)
        self.participation = Participation.objects.create(
            contest=self.contest, user=self.competitor, score=100
        )
        self.practice_session = PracticeSession.objects.create(
            contest=self.contest, user=self.competitor, score=1
        )
        Submission.objects.create(
            user=self.competitor,
            problem=self.problem,
            language="python",
            source_code="print(1)",
            contest=self.contest,
        )
        Submission.objects.create(
            user=self.competitor,
            problem=self.problem,
            language="python",
            source_code="print(2)",
            practice_session=self.practice_session,
        )
        self.reset_url = reverse(
            "admin:contests_contest_reset", args=[self.contest.pk]
        )
        self.client.force_login(self.admin)

    def test_change_page_has_reset_link(self):
        response = self.client.get(
            reverse("admin:contests_contest_change", args=[self.contest.pk])
        )

        self.assertContains(response, self.reset_url)
        self.assertContains(response, "Reset contest")

    def test_reset_requires_confirmation_and_preserves_problems(self):
        response = self.client.get(self.reset_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2 lượt nộp bài")
        self.assertEqual(Submission.objects.count(), 2)

        response = self.client.post(self.reset_url, follow=True)

        self.assertRedirects(
            response,
            reverse("admin:contests_contest_change", args=[self.contest.pk]),
        )
        self.assertFalse(Participation.objects.filter(contest=self.contest).exists())
        self.assertFalse(PracticeSession.objects.filter(contest=self.contest).exists())
        self.assertFalse(Submission.objects.exists())
        self.assertEqual(list(self.contest.problems.all()), [self.problem])
