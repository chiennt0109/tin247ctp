from __future__ import annotations

from judge.sandbox import SandboxManager


class JudgeWorker:
    def __init__(self):
        self.sandbox = SandboxManager()

    def run_submission(self, submission_id: int, run_callable):
        ctx = self.sandbox.create(submission_id)
        try:
            return run_callable(ctx)
        finally:
            self.sandbox.destroy(ctx)
