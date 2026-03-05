# path: submissions/views_callback.py
import os
import json
import logging
import redis

from django.http import JsonResponse, HttpResponseForbidden, HttpResponseNotFound
from django.views.decorators.csrf import csrf_exempt

from submissions.models import Submission

logger = logging.getLogger(__name__)

# Redis dùng cho SSE
r = redis.StrictRedis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))


@csrf_exempt
def judge_callback(request):
    """
    Callback từ worker sau khi chấm xong.
    Payload mẫu:
    {
        "submission_id": 123,
        "verdict": "Accepted",
        "passed": 5,
        "total": 5,
        "debug": [...]   # luôn là LIST
    }
    """
    # =============================
    # 🔐 1. Xác thực token
    # =============================
    token = request.headers.get("Authorization", "")
    expected = f"Bearer {os.getenv('JUDGE_TOKEN')}"

    if token != expected:
        logger.warning(f"[CALLBACK] Invalid token: {token}")
        return HttpResponseForbidden("Invalid token")

    # =============================
    # 📦 2. Parse JSON payload
    # =============================
    try:
        data = json.loads(request.body)
        sid = int(data.get("submission_id"))
        verdict = data.get("verdict", "Pending")
        passed = int(data.get("passed", 0))
        total = int(data.get("total", 0))
        debug_raw = data.get("debug", None)

        # đảm bảo debug luôn dạng list
        if isinstance(debug_raw, str):
            try:
                debug = json.loads(debug_raw)
            except Exception:
                debug = debug_raw
        else:
            debug = debug_raw

    except Exception as e:
        logger.error(f"[CALLBACK] ❌ Invalid JSON body: {e}")
        return JsonResponse({"ok": False, "error": "Invalid JSON"}, status=400)

    logger.info(f"[CALLBACK] Received for {sid}: {verdict} ({passed}/{total})")

    # =============================
    # 💾 3. Ghi vào DB
    # =============================
    try:
        sub = Submission.objects.get(id=sid)
    except Submission.DoesNotExist:
        logger.error(f"[CALLBACK] ❌ Submission {sid} not found")
        return HttpResponseNotFound("Submission not found")

    # Lưu theo chuẩn mới (debug là list)
    sub.verdict = verdict
    sub.passed_tests = passed
    sub.total_tests = total
    sub.exec_time = 0.0
    sub.debug_info = json.dumps(debug, ensure_ascii=False) if debug is not None else None

    sub.save(update_fields=[
        "verdict", "passed_tests", "total_tests",
        "debug_info", "exec_time"
    ])

    logger.info(f"[CALLBACK] ✅ Updated submission {sid}")
    

    # =======================================
    # ⭐ 3.5 – CẬP NHẬT ĐỘ KHÓ (AC rate)
    # =======================================
    try:
        problem = sub.problem

        # tăng số AC
        if verdict.lower() in ["accepted", "ac"]:
            problem.ac_count += 1

        # tăng tổng số submission
        problem.submission_count += 1

        # tự động điều chỉnh độ khó
        problem.auto_adjust_difficulty()

        # lưu dữ liệu
        problem.save(update_fields=["ac_count", "submission_count", "difficulty"])

        logger.info(
            f"[CALLBACK] 📊 Updated Problem Stats: "
            f"{problem.code} | AC={problem.ac_count} | Sub={problem.submission_count} | Diff={problem.difficulty}"
        )

    except Exception as e:
        logger.error(f"[CALLBACK] ❌ Error updating difficulty for submission {sid}: {e}")


    # =======================================
    # ⚡ UPDATE PRACTICE SCORING (per-user)
    # =======================================
    if sub.practice_session:
        from django.utils import timezone
        from django.db import transaction

        with transaction.atomic():
            sess = sub.practice_session.__class__.objects.select_for_update().get(
                id=sub.practice_session.id
            )

            now = timezone.now()

            # 1) Auto-lock nếu hết giờ
            if sess.end_time and now > sess.end_time:
                if not sess.is_locked:
                    sess.is_locked = True
                    sess.save(update_fields=["is_locked"])
                logger.info(
                    f"[CALLBACK] 🟥 Practice expired → không update điểm (user={sub.user.username})"
                )

            else:
                # 2) Session chưa khóa → kiểm tra AC lần đầu
                if not sess.is_locked:

                    already_ac = Submission.objects.filter(
                        practice_session=sess,
                        problem=sub.problem,
                        verdict="Accepted"
                    ).exclude(id=sub.id).exists()

                    # +1 điểm nếu AC lần đầu
                    if verdict == "Accepted" and not already_ac:
                        sess.score += 1

                    sess.last_submit = now
                    sess.save(update_fields=["score", "last_submit"])

                    logger.info(
                        f"[CALLBACK] 🟦 Practice updated: user={sub.user.username}, "
                        f"score={sess.score}, problem={sub.problem.code}, first_ac={not already_ac}"
                    )
                else:
                    logger.info(f"[CALLBACK] 🔒 Session locked → skip update")




    # =============================
    # 🚀 4. SSE publish (debug không cần gửi)
    # =============================
    try:
        payload = json.dumps(
            {
                "id": sid,
                "verdict": verdict,
                "passed": passed,
                "total": total,
                "is_done": verdict not in ["Pending", "Running"],
            },
            ensure_ascii=False
        )

        channel = f"sse_submission_{sid}"
        r.publish(channel, payload)

        logger.debug(f"[CALLBACK] 📢 SSE published on {channel}")

    except Exception as e:
        logger.warning(f"[CALLBACK] ⚠️ Redis publish failed: {e}")

    # =============================
    # 🎯 5. Trả phản hồi về worker
    # =============================
    return JsonResponse({
        "ok": True,
        "sid": sid,
        "verdict": verdict,
        "passed": passed,
        "total": total
    })
