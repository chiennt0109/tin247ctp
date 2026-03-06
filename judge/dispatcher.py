"""Submission dispatch layer for queue-based judging."""

from __future__ import annotations

import os
from typing import Any

from redis import Redis
from rq import Queue

from judge.worker import judge_submission_job

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
QUEUE_NAME = os.getenv("OJ_JUDGE_QUEUE", "judge")


class JudgeDispatcher:
    """Receive submission, push to queue, and expose result collection helper."""

    def __init__(self, redis_url: str | None = None, queue_name: str = QUEUE_NAME):
        self.redis = Redis.from_url(redis_url or REDIS_URL)
        self.queue = Queue(queue_name, connection=self.redis)

    def dispatch(self, submission_id: int):
        """Push job to RQ worker queue."""
        return self.queue.enqueue(judge_submission_job, submission_id)

    def collect_result(self, job_id: str) -> dict[str, Any] | None:
        """Collect finished job result if available."""
        job = self.queue.fetch_job(job_id)
        if not job:
            return None
        if job.is_finished:
            return job.result
        return None
