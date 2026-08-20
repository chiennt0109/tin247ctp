from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Problem, TestCase as ProblemTestCase


class ProblemAdminSampleInlineTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser(
            username="admin-problems",
            email="admin-problems@example.com",
            password="password",
        )
        cls.problem = Problem.objects.create(
            code="INLINE",
            title="Inline test visibility",
            statement="Statement",
        )
        cls.sample = ProblemTestCase.objects.create(
            problem=cls.problem,
            input_data="sample input marker",
            expected_output="sample output marker",
            is_sample=True,
        )
        cls.judge_test = ProblemTestCase.objects.create(
            problem=cls.problem,
            input_data="private judge input marker",
            expected_output="private judge output marker",
            is_sample=False,
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_change_form_only_contains_sample_tests(self):
        response = self.client.get(
            reverse("admin:problems_problem_change", args=[self.problem.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "sample input marker")
        self.assertContains(response, "sample output marker")
        self.assertNotContains(response, "private judge input marker")
        self.assertNotContains(response, "private judge output marker")

        inline_formset = response.context["inline_admin_formsets"][0].formset
        self.assertEqual(list(inline_formset.queryset), [self.sample])

    def test_inline_forces_new_tests_to_be_samples(self):
        response = self.client.get(
            reverse("admin:problems_problem_change", args=[self.problem.pk])
        )
        formset_class = type(response.context["inline_admin_formsets"][0].formset)
        prefix = response.context["inline_admin_formsets"][0].formset.prefix
        formset = formset_class(
            data={
                f"{prefix}-TOTAL_FORMS": "1",
                f"{prefix}-INITIAL_FORMS": "0",
                f"{prefix}-MIN_NUM_FORMS": "0",
                f"{prefix}-MAX_NUM_FORMS": "1000",
                f"{prefix}-0-is_sample": "",
                f"{prefix}-0-input_data": "new sample",
                f"{prefix}-0-expected_output": "new output",
            },
            instance=self.problem,
            prefix=prefix,
        )

        self.assertTrue(formset.is_valid(), formset.errors)
        new_test = formset.save()[0]
        self.assertTrue(new_test.is_sample)
        self.judge_test.refresh_from_db()
        self.assertFalse(self.judge_test.is_sample)
