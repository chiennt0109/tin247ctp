import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase

from judge.playground import PlaygroundResult, run_playground
from submissions.views import playground_run_api


def execution(return_code=0, stdout="", stderr="", timed_out=False, output_limited=False):
    return {
        "return_code": return_code, "stdout": stdout, "stderr": stderr,
        "elapsed": .02, "timed_out": timed_out, "output_limited": output_limited,
    }


class PlaygroundServiceTests(SimpleTestCase):
    def run_mocked(self, language, source, effects, stdin=""):
        with tempfile.TemporaryDirectory() as root, \
             patch("judge.playground.PLAYGROUND_ROOT", root), \
             patch("judge.playground.runner_health", return_value=(True, "ready")), \
             patch("judge.playground.os.chmod"), \
             patch("judge.playground._execute", side_effect=effects) as execute:
            return run_playground(language, source, stdin, time_limit=.1)

    def test_cpp_ok(self):
        result = self.run_mocked(
            "cpp17", "int main(){}",
            [execution(), execution(stdout="6\n")], "3\n1 2 3\n",
        )
        self.assertEqual((result.status, result.stdout), ("OK", "6\n"))

    def test_cpp_compile_error(self):
        result = self.run_mocked("cpp17", "int main(){return 0}", [execution(1, stderr="expected ;")])
        self.assertEqual(result.status, "CE")
        self.assertIn("expected ;", result.compile_output)

    def test_cpp_runtime_error(self):
        result = self.run_mocked("cpp17", "int main(){}", [execution(), execution(139, stderr="segfault")])
        self.assertEqual(result.status, "RE")

    def test_cpp_timeout(self):
        result = self.run_mocked("cpp17", "int main(){while(true){}}", [execution(), execution(124, timed_out=True)])
        self.assertEqual(result.status, "TLE")

    def test_python_ok(self):
        result = self.run_mocked("python", "print(sum(map(int,input().split())))", [execution(stdout="6\n")], "1 2 3\n")
        self.assertEqual(result.status, "OK")

    def test_python_runtime_error(self):
        result = self.run_mocked("python", "1/0", [execution(1, stderr="ZeroDivisionError")])
        self.assertEqual((result.status, result.stderr), ("RE", "ZeroDivisionError"))

    def test_python_timeout(self):
        result = self.run_mocked("python", "while True: pass", [execution(124, timed_out=True)])
        self.assertEqual(result.status, "TLE")


class PlaygroundApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.problem = SimpleNamespace(pk=7, code="SUM", time_limit=1, memory_limit=128)

    @patch("submissions.views.cache.add", return_value=True)
    @patch("submissions.views.run_playground", return_value=PlaygroundResult(stdout="6\n"))
    @patch("submissions.views.get_object_or_404")
    def test_custom_input_works_without_sample(self, get_object, runner, _cache):
        get_object.return_value = self.problem
        request = self.factory.post(
            "/api/playground/run/",
            data=json.dumps({"problem_code": "SUM", "language": "cpp17", "source": "code", "stdin": "3\n1 2 3\n"}),
            content_type="application/json",
        )
        request.user = SimpleNamespace(pk=12, is_authenticated=True)
        response = playground_run_api(request)
        self.assertEqual(response.status_code, 200)
        runner.assert_called_once_with("cpp17", "code", "3\n1 2 3\n", time_limit=1.0, memory_mb=128)

    def test_frontend_distinguishes_system_and_compile_errors(self):
        template = Path("templates/submissions/submit.html").read_text(encoding="utf-8")
        self.assertIn('data.status === "CE"', template)
        self.assertIn('data.status === "SYSTEM_ERROR"', template)
        self.assertIn("Lỗi biên dịch", template)
