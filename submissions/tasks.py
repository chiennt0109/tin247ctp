# path: submissions/tasks.py
import sys
import os
import json
import traceback
import logging
import importlib.util

from django.conf import settings
from .models import Submission
from judge.grader import grade_submission  # fallback local grader

logger = logging.getLogger(__name__)

# ================================
# 🔧 Load sandbox worker /srv/judge/worker.py
# ================================
SANDBOX_PATH = "/srv/judge/worker.py"
sandbox_worker = None
USE_EXTERNAL_SANDBOX_WORKER = os.getenv("OJ_USE_EXTERNAL_SANDBOX_WORKER", "false").lower() in {"1", "true", "yes"}

if os.path.exists(SANDBOX_PATH):
    try:
        spec = importlib.util.spec_from_file_location("sandbox_worker", SANDBOX_PATH)
        sandbox_worker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sandbox_worker)
        logger.info("[TASKS] ✅ Loaded sandbox worker from %s", SANDBOX_PATH)
    except Exception as e:
        sandbox_worker = None
        logger.exception("[TASKS] ❌ Failed to load sandbox worker: %s", e)
else:
    logger.warning("[TASKS] ⚠️ Sandbox worker file not found at %s", SANDBOX_PATH)


def _grade_local(sub: Submission):
    """
    Chấm local (không dùng sandbox) – dùng khi worker lỗi / không có.
    """
    try:
        verdict, exec_time, passed, total, debug = grade_submission(sub)
        sub.verdict = verdict
        sub.exec_time = float(exec_time or 0.0)
        sub.passed_tests = int(passed or 0)
        sub.total_tests = int(total or 0)

        try:
            sub.debug_info = json.dumps(debug, ensure_ascii=False)
        except Exception:
            sub.debug_info = str(debug)

        sub.save()
        logger.info("[TASK] ✅ Local grade xong submission %s: %s", sub.id, verdict)
    except Exception:
        sub.verdict = "Judge Error"
        sub.debug_info = traceback.format_exc()
        sub.save()
        logger.exception("[TASK] ❌ Lỗi khi chấm local submission %s", sub.id)


def judge_submission(submission_id: int):
    """
    Job chạy trên RQ worker (manage.py rqworker judge).

    - Nếu sandbox_worker (/srv/judge/worker.py) chạy được → gọi sandbox_worker.run_job
      và để callback cập nhật kết quả.
    - Nếu sandbox_worker không load được / bị lỗi → chấm local bằng grade_submission().
    """
    logger.info("[TASK] 🚀 Bắt đầu chấm submission %s", submission_id)
    sub = Submission.objects.get(id=submission_id)
    sub.verdict = "Running"
    sub.save(update_fields=["verdict"])

    # Mặc định chấm local để đảm bảo verdict/checker thống nhất với code trong repo.
    # Chỉ dùng sandbox worker ngoài khi bật tường minh qua OJ_USE_EXTERNAL_SANDBOX_WORKER=true
    if (not USE_EXTERNAL_SANDBOX_WORKER) or sandbox_worker is None or not hasattr(sandbox_worker, "run_job"):
        logger.warning(
            "[TASK] ⚠️ using local grader (external sandbox disabled or unavailable), "
            "fallback local cho submission %s",
            sub.id,
        )
        _grade_local(sub)
        return

    try:
        job_data = {
            "submission_id": sub.id,
            "problem_code": sub.problem.code,
            "language": sub.language,
            "source_code": sub.source_code,
        }

        logger.info(
            "[TASK] 📤 Gọi sandbox_worker.run_job cho submission %s (%s/%s)",
            sub.id,
            sub.user.username,
            sub.problem.code,
        )

        # run_job sẽ:
        #  - tự chạy docker
        #  - tự callback về Django (views_callback.judge_callback) để cập nhật DB
        result = sandbox_worker.run_job(job_data)

        # Chỉ log lại, không ghi verdict ở đây nữa
        if isinstance(result, dict):
            rv = result.get("verdict", "N/A")
        else:
            rv = getattr(result, "verdict", "N/A")

        logger.info(
            "[TASK] ✅ Sandbox đã xử lý submission %s, verdict (nếu có) = %s",
            sub.id,
            rv,
        )

    except Exception:
        logger.exception(
            "[TASK] ❌ Lỗi khi gọi sandbox_worker.run_job, fallback local cho submission %s",
            sub.id,
        )
        _grade_local(sub)
