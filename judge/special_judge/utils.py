def normalize_text(s: str) -> str:
    return (s or "").strip().replace("\r\n", "\n").rstrip()


def parse_config(config: str) -> dict:
    out = {}
    for part in (config or "").split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip().lower()] = v.strip()
        else:
            out[part.lower()] = "1"
    return out
