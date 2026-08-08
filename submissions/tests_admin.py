from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from problems.models import Problem

from .models import Submission


class SubmissionAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_superuser("admin", "admin@example.com", "password")
        cls.alice = User.objects.create_user("alice", "alice@example.com")
        cls.bob = User.objects.create_user("bob", "bob@example.com")
        problem = Problem.objects.create(code="SUM", title="Sum", statement="Add numbers")

        Submission.objects.create(
            user=cls.alice, problem=problem, language="python", source_code="", verdict="Accepted"
        )
        # Repeated Accepted submissions for one user/problem count as attempts,
        # but only as one submitted and one Accepted problem.
        Submission.objects.create(
            user=cls.alice, problem=problem, language="python", source_code="", verdict="Accepted"
        )
        Submission.objects.create(
            user=cls.alice, problem=problem, language="python", source_code="", verdict="Wrong Answer"
        )
        Submission.objects.create(
            user=cls.bob, problem=problem, language="cpp", source_code="", verdict="Accepted"
        )

    def setUp(self):
        self.client.force_login(self.admin)

    def test_changelist_shows_totals_and_per_user_summary(self):
        response = self.client.get(reverse("admin:submissions_submission_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["submission_totals"],
            {
                "submission_attempt_count": 4,
                "submitted_problem_count": 2,
                "accepted_problem_count": 2,
                "user_count": 2,
            },
        )
        summaries = list(response.context["submission_user_summary"])
        self.assertEqual(summaries[0]["user__username"], "alice")
        self.assertEqual(summaries[0]["submission_attempt_count"], 3)
        self.assertEqual(summaries[0]["submitted_problem_count"], 1)
        self.assertEqual(summaries[0]["accepted_problem_count"], 1)
        self.assertContains(response, "Thống kê bài nộp theo bộ lọc")

    def test_user_filter_is_applied_to_summary(self):
        response = self.client.get(
            reverse("admin:submissions_submission_changelist"),
            {"user__id__exact": self.bob.pk},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["submission_totals"],
            {
                "submission_attempt_count": 1,
                "submitted_problem_count": 1,
                "accepted_problem_count": 1,
                "user_count": 1,
            },
        )
        summaries = list(response.context["submission_user_summary"])
        self.assertEqual([item["user__username"] for item in summaries], ["bob"])
