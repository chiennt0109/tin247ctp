"""
Queue/dispatch facade. In production this is consumed by RQ worker processes.
"""

from judge.worker import JudgeWorker


class JudgeDispatcher:
    def __init__(self):
        self.worker = JudgeWorker()

    def dispatch(self, submission_id: int, run_callable):
        return self.worker.run_submission(submission_id, run_callable)
