import math
import time
from collections import Counter

from .result import SpecialJudgeResult
from .utils import parse_config


def _tok(s):
    return (s or "").split()


def _ints(s):
    return [int(x) for x in _tok(s)]


def _ok(msg="OK"):
    return SpecialJudgeResult(return_code=0, stdout=msg, mode="builtin")


def _wa(msg):
    return SpecialJudgeResult(return_code=1, stderr=msg, mode="builtin")


def _pe(msg):
    return SpecialJudgeResult(return_code=2, stderr=msg, mode="builtin")


def checker_permutation(inp, out, exp, config=""):
    vals = _ints(inp)
    if not vals:
        return _wa("missing n")
    n = vals[0]
    p = _ints(out)
    return _ok() if len(p) == n and set(p) == set(range(1, n + 1)) else _wa("not permutation")


def checker_matching(inp, out, exp, config=""):
    vals = _ints(inp)
    if len(vals) < 3:
        return _wa("invalid input")
    n1, n2, m = vals[0], vals[1], vals[2]
    flat = vals[3:]
    if len(flat) < 2 * m:
        return _wa("invalid edges")
    edges = {(flat[2 * i], flat[2 * i + 1]) for i in range(m)}
    o = _ints(out)
    if len(o) % 2:
        return _wa("invalid matching output")
    pairs = [(o[i], o[i + 1]) for i in range(0, len(o), 2)]
    if any(a < 1 or a > n1 or b < 1 or b > n2 for a, b in pairs):
        return _wa("vertex out of range")
    if any((a, b) not in edges for a, b in pairs):
        return _wa("edge missing")
    if any(v > 1 for v in Counter(a for a, _ in pairs).values()):
        return _wa("left duplicated")
    if any(v > 1 for v in Counter(b for _, b in pairs).values()):
        return _wa("right duplicated")
    return _ok()


def checker_set_compare(inp, out, exp, config=""):
    return _ok() if sorted(_tok(out)) == sorted(_tok(exp)) else _wa("set mismatch")


def checker_numeric_tolerance(inp, out, exp, config=""):
    cfg = parse_config(config)
    eps = float(cfg.get("eps", "1e-6"))
    a = [float(x) for x in _tok(out)]
    b = [float(x) for x in _tok(exp)]
    if len(a) != len(b):
        return _wa("token mismatch")
    for x, y in zip(a, b):
        if math.fabs(x - y) > eps:
            return _wa("difference exceeds eps")
    return _ok()


def checker_euler_path(inp, out, exp, config=""):
    vals = _ints(inp)
    if len(vals) < 2:
        return _wa("invalid input")
    n, m = vals[0], vals[1]
    flat = vals[2:]
    if len(flat) < 2 * m:
        return _wa("invalid edges")
    edges = [(flat[2 * i], flat[2 * i + 1]) for i in range(m)]

    o = _tok(out)
    e = _tok(exp)
    impossible = {"-1", "NO", "IMPOSSIBLE", "NONE"}
    if o and o[0].upper() in impossible:
        return _ok() if e and e[0].upper() in impossible else _wa("claimed impossible")

    if o and o[0].upper() in {"YES", "POSSIBLE"}:
        o = o[1:]
    try:
        path = [int(x) for x in o]
    except Exception:
        return _pe("invalid output format")
    if len(path) == m + 2 and path[0] == m + 1:
        path = path[1:]
    if len(path) != m + 1:
        return _wa("path length")
    if any(x < 1 or x > n for x in path):
        return _wa("vertex range")

    cfg = parse_config(config)
    directed = cfg.get("directed", "0") in {"1", "true", "yes"}

    cnt = Counter((u, v) if directed else (min(u, v), max(u, v)) for u, v in edges)
    for i in range(m):
        u, v = path[i], path[i + 1]
        k = (u, v) if directed else (min(u, v), max(u, v))
        if cnt[k] <= 0:
            return _wa("invalid edge usage")
        cnt[k] -= 1
    if any(v != 0 for v in cnt.values()):
        return _wa("not all edges used")
    return _ok()


def checker_grid(inp, out, exp, config=""):
    vals = _ints(inp)
    if len(vals) < 2:
        return _wa("invalid input")
    r, c = vals[0], vals[1]
    lines = [x.strip() for x in (out or "").splitlines() if x.strip()]
    if len(lines) != r:
        return _wa("row mismatch")
    rows = [ln.split() for ln in lines]
    if any(len(row) != c for row in rows):
        return _wa("col mismatch")
    return _ok()


def checker_constructive(inp, out, exp, config=""):
    if not _tok(out):
        return _wa("empty output")
    return _ok()


def checker_geometry(inp, out, exp, config=""):
    # Generic geometry fallback: compare as set of tokens unless eps provided for floats.
    cfg = parse_config(config)
    if "eps" in cfg:
        return checker_numeric_tolerance(inp, out, exp, config)
    return checker_set_compare(inp, out, exp, config)


BUILTIN = {
    "permutation": checker_permutation,
    "matching": checker_matching,
    "set_compare": checker_set_compare,
    "numeric_tolerance": checker_numeric_tolerance,
    "float_tolerance": checker_numeric_tolerance,
    "euler_path": checker_euler_path,
    "grid": checker_grid,
    "geometry": checker_geometry,
    "constructive": checker_constructive,
}


def run_builtin_checker(checker_type, input_data, output_data, expected_data, config="") -> SpecialJudgeResult:
    start = time.perf_counter()
    fn = BUILTIN.get(checker_type)
    if not fn:
        res = SpecialJudgeResult(return_code=3, stderr=f"unknown builtin checker: {checker_type}", mode="builtin")
    else:
        try:
            res = fn(input_data, output_data, expected_data, config)
        except Exception as exc:
            res = SpecialJudgeResult(return_code=3, stderr=f"builtin checker exception: {exc}", mode="builtin")
    res.time = time.perf_counter() - start
    return res
