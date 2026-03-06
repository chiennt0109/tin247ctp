import unittest

from judge.runner import ProgramBundle, _build_docker_cmd, _to_container_cmd


class RunnerDockerTests(unittest.TestCase):
    def test_container_path_mapping(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        self.assertEqual(_to_container_cmd(b), ["/workspace/main"])

    def test_docker_flags_present(self):
        b = ProgramBundle(language="cpp", run_cmd=["/tmp/sub/main"], workdir="/tmp/sub")
        cmd = _build_docker_cmd(b)
        s = " ".join(cmd)
        self.assertIn("--network=none", s)
        self.assertIn("--memory=512m", s)
        self.assertIn("--cpus=1", s)
        self.assertIn("--pids-limit=64", s)
        self.assertIn("--read-only", s)


if __name__ == "__main__":
    unittest.main()
