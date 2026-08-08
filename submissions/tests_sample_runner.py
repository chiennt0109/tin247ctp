import json
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from submissions.views import run_sample


class SampleRunnerErrorHandlingTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.problem = SimpleNamespace(pk=7, time_limit=1, memory_limit=128)

    def request(self, **data):
        request = self.factory.post("/submissions/7/run-sample/", data)
        request.user = SimpleNamespace(pk=12, is_authenticated=True)
        return request

    @patch("submissions.views.get_object_or_404")
    def test_rejects_unsupported_language_as_json(self, get_object):
        get_object.return_value = self.problem
        response = run_sample(self.request(language="java", source="class Main {}"), 7)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response["Content-Type"], "application/json")

    @patch("submissions.views.SandboxManager.create", side_effect=RuntimeError("docker unavailable"))
    @patch("submissions.views.cache.add", side_effect=ConnectionError("redis unavailable"))
    @patch("submissions.views.get_object_or_404")
    def test_cache_and_runner_failures_still_return_json(self, get_object, _cache, _sandbox):
        get_object.return_value = self.problem
        response = run_sample(self.request(language="cpp", source="int main(){}"), 7)
        payload = json.loads(response.content)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(payload["verdict"], "JE")
        self.assertIn("Docker", payload["error"])
