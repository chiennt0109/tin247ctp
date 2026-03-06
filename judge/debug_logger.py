import json
import os
from datetime import datetime

LOG_PATH = "/var/log/tin247ctp/judge_debug.log"


def log_test_event(payload: dict):
    payload = dict(payload)
    payload["ts"] = datetime.utcnow().isoformat() + "Z"
    line = json.dumps(payload, ensure_ascii=False)

    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        # never break judging because logging failed
        pass
