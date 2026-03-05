# path: submissions/views_api.py
import json
import time
import redis
import logging

from django.http import JsonResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from submissions.models import Submission

logger = logging.getLogger(__name__)

# Redis kết nối để lắng nghe thông báo realtime
r = redis.StrictRedis.from_url("redis://localhost:6379/0")


# ===========================================================
# 🎧 1. SSE STREAM - Kênh realtime (Server-Sent Events)
# ===========================================================
def submission_stream(request, sid):
    """
    Stream realtime cho 1 submission (SSE).
    """
    sid = int(sid)
    logger.info(f"👂 SSE client connected for submission {sid}")

    sub = get_object_or_404(Submission, pk=sid)

    # Nếu bài đã xong → trả luôn dữ liệu rồi đóng
    if sub.verdict not in ["Pending", "Running"]:
        payload = json.dumps(
            {
                "id": sid,
                "verdict": sub.verdict,
                "passed": sub.passed_tests or 0,
                "total": sub.total_tests or 0,
                "exec_time": getattr(sub, "exec_time", 0.0),
                "is_done": True,
                "debug": _load_debug(sub.debug_info),
            },
            ensure_ascii=False,
        )

        logger.info(f"✅ SSE immediate send for completed submission {sid}")
        return StreamingHttpResponse(
            f"data: {payload}\n\n", content_type="text/event-stream"
        )

    # Nếu chưa xong, lắng nghe redis pubsub
    pubsub = r.pubsub()
    channel = f"sse_submission_{sid}"
    pubsub.subscribe(channel)

    def event_stream():
        last_heartbeat = time.time()

        try:
            for msg in pubsub.listen():
                # Heartbeat gửi đều đặn 10s
                if msg["type"] != "message":
                    if time.time() - last_heartbeat > 10:
                        yield ":\n\n"
                        last_heartbeat = time.time()
                    continue

                # Dữ liệu nhận từ redis
                raw = msg["data"].decode("utf-8")
                yield f"data: {raw}\n\n"

                try:
                    obj = json.loads(raw)
                    if obj.get("is_done"):
                        break
                except Exception as e:
                    logger.warning(f"⚠️ SSE parse error: {e}")

        finally:
            pubsub.unsubscribe(channel)
            pubsub.close()
            yield "event: close\ndata: {}\n\n"
            logger.info(f"🔚 SSE disconnected for submission {sid}")

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")


# ===========================================================
# 📊 2. JSON fallback - frontend polling
# ===========================================================
def submission_json(request, sid):
    """
    Poll kết quả submission dưới dạng JSON.
    """
    sid = int(sid)
    sub = get_object_or_404(Submission, pk=sid)

    data = {
        "id": sid,
        "verdict": sub.verdict,
        "passed": sub.passed_tests or 0,
        "total": sub.total_tests or 0,
        "exec_time": getattr(sub, "exec_time", 0.0),
        "is_done": sub.verdict not in ["Pending", "Running"],
        "debug": _load_debug(sub.debug_info),   # ⚡ DEBUG luôn là list
    }

    logger.debug(
        f"[JSON] sid={sid} verdict={sub.verdict} "
        f"({data['passed']}/{data['total']})"
    )

    response = JsonResponse(data)
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


# ===========================================================
# 🧩 Helper: load debug JSON
# ===========================================================
def _load_debug(raw):
    """
    Convert debug_info từ DB thành dạng list:
    - Nếu raw là JSON string -> parse.
    - Nếu raw là list -> giữ nguyên.
    - Nếu None -> trả về None.
    """
    if raw is None:
        return None

    if isinstance(raw, list):
        return raw

    try:
        return json.loads(raw)
    except Exception:
        return raw  # fallback dạng string
