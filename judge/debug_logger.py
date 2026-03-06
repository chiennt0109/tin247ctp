import json
import os
from datetime import datetime

LOG_PATH = "/var/log/tin247ctp/judge_debug.log"


def _safe(v):
    if isinstance(v, bytes):
        return v.decode("utf-8", errors="replace")
    return v


def log_test_event(payload: dict):
    payload = dict(payload)
    payload["ts"] = datetime.utcnow().isoformat() + "Z"
    safe_payload = {k: _safe(v) for k, v in payload.items()}
    line = json.dumps(safe_payload, ensure_ascii=False)

    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # never break judging because logging failed
        pass

