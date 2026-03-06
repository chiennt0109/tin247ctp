import logging

from judge.worker import judge_submission_job

logger = logging.getLogger(__name__)


def judge_submission(submission_id: int):
    """RQ entrypoint: dispatch to judge worker pipeline (sandbox -> checker -> verdict)."""
    logger.info("[TASK] dispatch submission %s", submission_id)
    return judge_submission_job(submission_id)
