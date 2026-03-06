import unittest

from unittest.mock import patch

from judge.runner import ProgramBundle, _build_docker_cmd, _to_container_cmd, compile_submission, run_case


class RunnerDockerTests(unittest.TestCase):
    def test_container_path_mapping(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        self.assertEqual(_to_container_cmd(b), ["/workspace/main"])

    def test_docker_flags_present(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        cmd = _build_docker_cmd(b, memory_limit_mb=256, time_limit=1.5)
        s = " ".join(cmd)
        self.assertIn("--network=none", s)
        self.assertIn("--memory=256m", s)
        self.assertIn("--cpus=1", s)
        self.assertIn("--pids-limit=64", s)
        self.assertIn("--read-only", s)
        self.assertIn("--ulimit", s)
        self.assertIn("cpu=3", s)



    def test_docker_timeout_includes_overhead(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")

        class _Proc:
            returncode = 0
            stderr = b""

        from unittest.mock import mock_open
        with patch("judge.runner.USE_DOCKER", True), \
             patch("judge.runner._build_docker_cmd", return_value=["docker", "run"]), \
             patch("judge.runner.subprocess.run", return_value=_Proc()) as run_mock, \
             patch("builtins.open", mock_open(read_data=b"")), \
             patch("judge.runner.tempfile.NamedTemporaryFile") as ntf:
            ntf.return_value.__enter__.return_value.name = "/tmp/sub/in.txt"
            ntf.return_value.__enter__.return_value.write = lambda *_: None
            run_case(b, "", time_limit=1.0, memory_limit_mb=128)

        self.assertGreaterEqual(run_mock.call_args.kwargs["timeout"], 3.0)

    def test_run_case_timeout_infinite_loop(self):
        bundle, err = compile_submission("python", "while True:\n    pass\n", "/tmp/test_runner")
        self.assertIsNotNone(bundle, err)
        with patch("judge.runner.USE_DOCKER", False):
            res = run_case(bundle, "", time_limit=0.2, memory_limit_mb=128)
        self.assertEqual(res["return_code"], 124)


if __name__ == "__main__":
    unittest.main()
