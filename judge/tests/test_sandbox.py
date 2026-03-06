import os
import stat
import unittest

from judge.sandbox import SandboxManager


class SandboxPermissionTests(unittest.TestCase):
    def test_workspace_is_container_readable(self):
        mgr = SandboxManager(base_dir="/tmp/tin247ctp_sandbox_test")
        ctx = mgr.create(42)
        try:
            mode = stat.S_IMODE(os.stat(ctx.root_dir).st_mode)
            self.assertEqual(mode, 0o755)
        finally:
            mgr.destroy(ctx)


if __name__ == "__main__":
    unittest.main()
