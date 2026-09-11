from datetime import timedelta

from django.contrib.auth.models import AnonymousUser, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Contest


class ContestVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.allowed_user = User.objects.create_user(username="allowed-user")
        cls.other_user = User.objects.create_user(username="other-user")
        now = timezone.now()
        cls.open_contest = Contest.objects.create(
            name="Contest cho tất cả",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        cls.restricted_contest = Contest.objects.create(
            name="Contest giới hạn",
            start_time=now - timedelta(hours=1),
            end_time=now + timedelta(hours=1),
        )
        cls.restricted_contest.allowed_users.add(cls.allowed_user)

    def test_empty_allowed_users_means_visible_to_everyone(self):
        self.assertTrue(self.open_contest.is_visible_to(AnonymousUser()))
        self.assertTrue(self.open_contest.is_visible_to(self.other_user))

    def test_restricted_contest_is_only_visible_to_selected_users(self):
        self.assertTrue(self.restricted_contest.is_visible_to(self.allowed_user))
        self.assertFalse(self.restricted_contest.is_visible_to(self.other_user))
        self.assertFalse(self.restricted_contest.is_visible_to(AnonymousUser()))

    def test_list_hides_restricted_contest_from_unselected_user(self):
        self.client.force_login(self.other_user)

        response = self.client.get(reverse("contests:contest_list"))

        self.assertContains(response, self.open_contest.name)
        self.assertNotContains(response, self.restricted_contest.name)

    def test_selected_user_can_open_restricted_contest(self):
        self.client.force_login(self.allowed_user)

        response = self.client.get(
            reverse("contests:contest_detail", args=[self.restricted_contest.pk])
        )

        self.assertEqual(response.status_code, 200)

    def test_unselected_user_gets_404_for_restricted_contest(self):
        self.client.force_login(self.other_user)

        response = self.client.get(
            reverse("contests:contest_detail", args=[self.restricted_contest.pk])
        )

        self.assertEqual(response.status_code, 404)
