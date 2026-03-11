from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from problems.models import Problem
from submissions.models import Submission

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


    def test_recent_activity_column_default_order_param(self):
        request = RequestFactory().get("/admin/auth/user/")
        self.assertEqual(self.model_admin._recent_activity_order_param(request), "-6")


class AdminRecentActivityOrderingTests(TestCase):
    def setUp(self):
        self.site = AdminSite()
        self.model_admin = UserAnalyticsAdmin(get_user_model(), self.site)
        self.user_model = get_user_model()

    def test_get_queryset_prioritizes_recent_submission_activity(self):
        old_login_user = self.user_model.objects.create_user(
            username="old_login_user", password="x", last_login=timezone.now() - timezone.timedelta(days=5)
        )
        active_submitter = self.user_model.objects.create_user(username="active_submitter", password="x")

        Submission.objects.create(
            user=active_submitter,
            problem=Problem.objects.create(code="P-ADMIN-1", title="P", statement="S"),
            language="python",
            source_code="print(1)",
            verdict="Accepted",
        )

        request = RequestFactory().get("/admin/auth/user/")
        request.user = old_login_user
        users = list(self.model_admin.get_queryset(request)[:2])
        self.assertEqual(users[0].username, "active_submitter")

    def test_get_ordering_does_not_override_queryset_activity_sort(self):
        request = RequestFactory().get("/admin/auth/user/")
        self.assertEqual(self.model_admin.get_ordering(request), ())

    def test_get_queryset_falls_back_to_last_login_when_no_submissions(self):
        stale_user = self.user_model.objects.create_user(
            username="stale_user", password="x", last_login=timezone.now() - timezone.timedelta(days=7)
        )
        fresh_user = self.user_model.objects.create_user(
            username="fresh_user", password="x", last_login=timezone.now() - timezone.timedelta(hours=3)
        )

        request = RequestFactory().get("/admin/auth/user/")
        request.user = fresh_user
        users = list(self.model_admin.get_queryset(request)[:2])
        self.assertEqual([u.username for u in users], ["fresh_user", "stale_user"])


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


class NewFeatureSmokeTests(SimpleTestCase):
    def test_keyword_skill_map_contains_expected_items(self):
        from learning_analytics.skill_detector import KEYWORD_SKILL_MAP

        self.assertEqual(KEYWORD_SKILL_MAP["bfs"], "BFS")
        self.assertEqual(KEYWORD_SKILL_MAP["dijkstra"], "Dijkstra")

    @patch("learning_analytics.api.SkillCoverageAnalyzer")
    def test_skill_coverage_api(self, analyzer_mock):
        from learning_analytics.api import skill_coverage

        analyzer_mock.return_value.analyze.return_value = {"missing_skills": ["BFS"]}
        request = RequestFactory().get("/api/skill_coverage")
        request.user = SimpleNamespace(is_staff=True, is_active=True, is_authenticated=True)
        response = skill_coverage(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"missing_skills", response.content)

    @patch("learning_analytics.api.RoadmapBuilder")
    def test_roadmap_track_api(self, builder_mock):
        from learning_analytics.api import roadmap_track

        builder_mock.return_value.get_track.return_value = {"track": "Graph Track", "steps": []}
        request = RequestFactory().get("/api/roadmap/graph")
        response = roadmap_track(request, "graph")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Graph Track", response.content)

    @patch("learning_analytics.api.LearningLeaderboardService")
    def test_learning_leaderboard_api(self, lb_mock):
        from learning_analytics.api import learning_leaderboard

        lb_mock.return_value.compute.return_value = {"hardworking": [], "breakthrough": [], "needs_improvement": []}
        request = RequestFactory().get("/api/learning_leaderboard")
        response = learning_leaderboard(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"hardworking", response.content)


    @patch("learning_analytics.api.User")
    @patch("learning_analytics.api.UserSkillStats")
    def test_student_skill_mastery_api(self, stat_model, user_model):
        from learning_analytics.api import student_skill_mastery

        fake_user = SimpleNamespace(id=1)
        user_model.objects.get.return_value = fake_user
        stat_model.objects.filter.return_value.select_related.return_value.order_by.return_value = [
            SimpleNamespace(skill=SimpleNamespace(name="BFS"), mastery_score=72.5, solved_problems=5, attempts=8, successes=5)
        ]
        request = RequestFactory().get('/api/student/1/skill_mastery')
        response = student_skill_mastery(request, 1)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"skill_mastery", response.content)


class SkillDetectorLogicTests(SimpleTestCase):
    @patch("learning_analytics.skill_detector.Skill")
    def test_normalize_and_detect_scores(self, skill_model):
        from learning_analytics.skill_detector import detect_skill_scores, normalize_text

        self.assertEqual(normalize_text("Shortest-Path!!!"), "shortest-path")

        skill_model.objects.all.return_value = [
            SimpleNamespace(name="BFS", slug="bfs"),
            SimpleNamespace(name="Dijkstra", slug="dijkstra"),
        ]

        problem = SimpleNamespace(
            title="Shortest Path in Grid",
            statement="Use BFS or Dijkstra for shortest path.",
            tags=SimpleNamespace(all=lambda: [SimpleNamespace(name="graph", slug="bfs")]),
        )
        scores = detect_skill_scores(problem)
        self.assertIn("BFS", scores)
        self.assertIn("Dijkstra", scores)
        self.assertGreaterEqual(scores["BFS"], 2)
