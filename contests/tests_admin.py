from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from problems.models import Problem


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
