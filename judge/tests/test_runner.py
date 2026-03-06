import unittest
import os
import stat

from unittest.mock import patch

from judge.runner import ProgramBundle, _build_docker_cmd, _to_container_cmd, compile_submission, run_case


class RunnerDockerTests(unittest.TestCase):
    def test_container_path_mapping(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        self.assertEqual(_to_container_cmd(b), ["./main"])

    def test_docker_flags_present(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        cmd = _build_docker_cmd(b, memory_limit_mb=256, time_limit=1.5)
        s = " ".join(cmd)
        self.assertIn("--network=none", s)
        self.assertIn("--memory=256m", s)
        self.assertIn("--cpus=1", s)
        self.assertIn("--pids-limit=64", s)
        self.assertIn("--read-only", s)
        self.assertIn("/bin/sh -c", s)
        self.assertIn("./main", s)
        self.assertNotIn("--ulimit", s)

    def test_docker_ulimit_flags_opt_in(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        with patch.dict("os.environ", {"OJ_DOCKER_USE_ULIMIT": "true"}):
            cmd = _build_docker_cmd(b, memory_limit_mb=256, time_limit=1.5)
        s = " ".join(cmd)
        self.assertIn("--ulimit", s)
        self.assertIn("cpu=3", s)

    def test_docker_timeout_includes_overhead(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")

        class _Proc:
            returncode = 0
            stderr = b""

        def fake_open(path, mode="r", *args, **kwargs):
            import io
            if "rb" in mode:
                return io.BytesIO(b"")
            return io.BytesIO()

        with patch("judge.runner.USE_DOCKER", True), \
             patch("judge.runner._build_docker_cmd", return_value=["docker", "run"]), \
             patch("judge.runner.subprocess.run", return_value=_Proc()) as run_mock, \
             patch("builtins.open", side_effect=fake_open):
            run_case(b, "", time_limit=1.0, memory_limit_mb=128)

        self.assertGreaterEqual(run_mock.call_args.kwargs["timeout"], 3.0)

    def test_run_case_timeout_infinite_loop(self):
        bundle, err = compile_submission("python", "while True:\n    pass\n", "/tmp/test_runner")
        self.assertIsNotNone(bundle, err)
        with patch("judge.runner.USE_DOCKER", False):
            res = run_case(bundle, "", time_limit=0.2, memory_limit_mb=128)
        self.assertEqual(res["return_code"], 124)

    def test_compile_python_sets_readable_permissions(self):
        bundle, err = compile_submission("python", "print(1)\n", "/tmp/test_runner_perm")
        self.assertIsNotNone(bundle, err)
        py_path = os.path.join(bundle.workdir, "main.py")
        mode = stat.S_IMODE(os.stat(py_path).st_mode)
        self.assertEqual(mode, 0o644)


if __name__ == "__main__":
    unittest.main()
