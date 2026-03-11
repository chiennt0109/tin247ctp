from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase

from learning_analytics.admin import UserAnalyticsAdmin
from learning_analytics.profile_service import LearningProfileService
from learning_analytics.serializers import (
    serialize_learning_path,
    serialize_problem_recommendation,
    serialize_user_skill,
)


class SerializerTests(SimpleTestCase):
    def test_serialize_user_skill(self):
        item = SimpleNamespace(
            skill=SimpleNamespace(name="BFS"),
            skill_score=0.75,
            level="intermediate",
            weakness_score=0.21,
            last_updated=None,
        )
        data = serialize_user_skill(item)
        self.assertEqual(data["skill"], "BFS")
        self.assertEqual(data["score"], 0.75)

    def test_serialize_problem_recommendation(self):
        rec = {
            "problem": SimpleNamespace(id=1, code="P1", title="Test", difficulty="Easy"),
            "skill": "BFS",
            "score": 0.9,
        }
        data = serialize_problem_recommendation(rec)
        self.assertEqual(data["code"], "P1")
        self.assertEqual(data["skill"], "BFS")

    def test_serialize_learning_path(self):
        skill = SimpleNamespace(name="DFS")
        data = serialize_learning_path(skill, 2)
        self.assertEqual(data, {"order": 2, "skill": "DFS"})


class ServiceLogicTests(SimpleTestCase):
    def test_mastery_label(self):
        self.assertEqual(LearningProfileService.mastery_label(0.2), "Weak")
        self.assertEqual(LearningProfileService.mastery_label(0.5), "Learning")
        self.assertEqual(LearningProfileService.mastery_label(0.7), "Good")
        self.assertEqual(LearningProfileService.mastery_label(0.9), "Mastered")


class AdminIntegrationTests(SimpleTestCase):
    def setUp(self):
        self.site = AdminSite()
        self.model_admin = UserAnalyticsAdmin(get_user_model(), self.site)

    def test_learning_profile_link(self):
        obj = SimpleNamespace(id=99)
        html = self.model_admin.learning_profile_link(obj)
        self.assertIn("Learning Profile", html)
        self.assertIn("/learning-analytics/admin/user/99/", html)

    def test_learning_profile_button(self):
        obj = SimpleNamespace(id=7, pk=7)
        html = self.model_admin.learning_profile_button(obj)
        self.assertIn("View Learning Profile", html)
        self.assertIn("/learning-analytics/admin/user/7/", html)


class ApiAdminEndpointTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("learning_analytics.api.LearningProfileService")
    @patch("learning_analytics.api.User")
    def test_admin_user_learning_profile_requires_staff(self, user_mock, service_mock):
        from learning_analytics.api import admin_user_learning_profile

        request = self.factory.get("/api/admin/user/1/learning_profile")
        request.user = SimpleNamespace(is_staff=False, is_active=True, is_authenticated=True)

        response = admin_user_learning_profile(request, 1)
        self.assertEqual(response.status_code, 302)

    @patch("learning_analytics.api.LearningProfileService")
    @patch("learning_analytics.api.User")
    def test_admin_user_learning_profile_success(self, user_mock, service_mock):
        from learning_analytics.api import admin_user_learning_profile

        service_mock.return_value.build_profile.return_value = {"overview": {"username": "u"}}
        request = self.factory.get("/api/admin/user/1/learning_profile")
        request.user = SimpleNamespace(is_staff=True, is_active=True, is_authenticated=True)

        response = admin_user_learning_profile(request, 1)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"overview", response.content)
