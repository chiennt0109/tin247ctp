import unittest

from unittest.mock import patch

from judge.runner import ProgramBundle, _build_docker_cmd, _to_container_cmd, compile_submission, run_case


class RunnerDockerTests(unittest.TestCase):
    def test_container_path_mapping(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        self.assertEqual(_to_container_cmd(b), ["/workspace/main"])

    def test_docker_flags_present(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        cmd = _build_docker_cmd(b, memory_limit_mb=256)
        s = " ".join(cmd)
        self.assertIn("--network=none", s)
        self.assertIn("--memory=256m", s)
        self.assertIn("--cpus=1", s)
        self.assertIn("--pids-limit=64", s)
        self.assertIn("--read-only", s)


    def test_run_case_timeout_infinite_loop(self):
        bundle, err = compile_submission("python", "while True:\n    pass\n", "/tmp/test_runner")
        self.assertIsNotNone(bundle, err)
        with patch("judge.runner.USE_DOCKER", False):
            res = run_case(bundle, "", time_limit=0.2, memory_limit_mb=128)
        self.assertEqual(res["return_code"], 124)


if __name__ == "__main__":
    unittest.main()
