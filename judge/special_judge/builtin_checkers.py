import math
import time
from collections import Counter

from .utils import parse_config


def _tokens(s: str):
    return (s or "").split()


def _ints(s: str):
    return [int(x) for x in _tokens(s)]


def _ret(code: int, out: str = "", err: str = ""):
    return {"return_code": code, "stdout": out, "stderr": err}


def check_permutation(input_data, contestant_output, expected_output, config=""):
    vals = _ints(input_data)
    if not vals:
        return _ret(1, err="missing n")
    n = vals[0]
    arr = _ints(contestant_output)
    if len(arr) != n:
        return _ret(1, err="length mismatch")
    if any(x < 1 or x > n for x in arr):
        return _ret(1, err="value out of range")
    return _ret(0) if len(set(arr)) == n else _ret(1, err="duplicate values")


def check_set_compare(input_data, contestant_output, expected_output, config=""):
    return _ret(0) if set(_tokens(contestant_output)) == set(_tokens(expected_output)) else _ret(1, err="set mismatch")


def check_numeric(input_data, contestant_output, expected_output, config=""):
    cfg = parse_config(config)
    eps = float(cfg.get("eps", "1e-6"))
    a = [float(x) for x in _tokens(contestant_output)]
    b = [float(x) for x in _tokens(expected_output)]
    if len(a) != len(b):
        return _ret(1, err="token count mismatch")
    for x, y in zip(a, b):
        if math.fabs(x - y) > eps:
            return _ret(1, err="difference exceeds eps")
    return _ret(0)


def _parse_graph(input_data):
    vals = _ints(input_data)
    if len(vals) < 2:
        return None
    n, m = vals[0], vals[1]
    flat = vals[2:]
    if len(flat) < 2 * m:
        return None
    edges = [(flat[2 * i], flat[2 * i + 1]) for i in range(m)]
    return n, m, edges


def check_euler(input_data, contestant_output, expected_output, config=""):
    parsed = _parse_graph(input_data)
    if not parsed:
        return _ret(1, err="invalid input")
    n, m, edges = parsed

    out_tok = _tokens(contestant_output)
    exp_tok = _tokens(expected_output)
    impossible = {"-1", "NO", "IMPOSSIBLE", "NONE"}
    if out_tok and out_tok[0].upper() in impossible:
        return _ret(0) if exp_tok and exp_tok[0].upper() in impossible else _ret(1, err="claimed impossible")

    if out_tok and out_tok[0].upper() in {"YES", "POSSIBLE"}:
        out_tok = out_tok[1:]
    try:
        path = [int(x) for x in out_tok]
    except Exception:
        return _ret(2, err="non-integer output")
    if len(path) == m + 2 and path[0] == m + 1:
        path = path[1:]
    if len(path) != m + 1:
        return _ret(1, err="path length mismatch")
    if any(x < 1 or x > n for x in path):
        return _ret(1, err="vertex out of range")

    directed = parse_config(config).get("directed", "0") in {"1", "true", "yes"}
    cnt = Counter((u, v) if directed else (min(u, v), max(u, v)) for u, v in edges)
    for i in range(m):
        u, v = path[i], path[i + 1]
        key = (u, v) if directed else (min(u, v), max(u, v))
        if cnt[key] <= 0:
            return _ret(1, err="invalid edge usage")
        cnt[key] -= 1
    return _ret(0) if all(v == 0 for v in cnt.values()) else _ret(1, err="not all edges used")


def check_graph_path(input_data, contestant_output, expected_output, config=""):
    parsed = _parse_graph(input_data)
    if not parsed:
        return _ret(1, err="invalid input")
    n, _m, edges = parsed
    directed = parse_config(config).get("directed", "0") in {"1", "true", "yes"}
    edge_set = set(edges)
    if not directed:
        edge_set |= {(v, u) for (u, v) in edge_set}
    try:
        path = [int(x) for x in _tokens(contestant_output)]
    except Exception:
        return _ret(2, err="non-integer output")
    if not path:
        return _ret(2, err="empty path")
    if any(x < 1 or x > n for x in path):
        return _ret(1, err="vertex out of range")
    for i in range(len(path) - 1):
        if (path[i], path[i + 1]) not in edge_set:
            return _ret(1, err="edge missing")
    return _ret(0)


def check_matching(input_data, contestant_output, expected_output, config=""):
    vals = _ints(input_data)
    if len(vals) < 3:
        return _ret(1, err="invalid input")
    n1, n2, m = vals[0], vals[1], vals[2]
    flat = vals[3:]
    if len(flat) < 2 * m:
        return _ret(1, err="invalid edges")
    edges = {(flat[2 * i], flat[2 * i + 1]) for i in range(m)}
    out = _ints(contestant_output)
    if len(out) % 2:
        return _ret(2, err="invalid pair formatting")
    pairs = [(out[i], out[i + 1]) for i in range(0, len(out), 2)]
    used_left, used_right = set(), set()
    for a, b in pairs:
        if not (1 <= a <= n1 and 1 <= b <= n2):
            return _ret(1, err="vertex out of range")
        if (a, b) not in edges:
            return _ret(1, err="edge missing")
        if a in used_left or b in used_right:
            return _ret(1, err="duplicate matched vertex")
        used_left.add(a)
        used_right.add(b)
    return _ret(0)


def check_constructive(input_data, contestant_output, expected_output, config=""):
    cfg = parse_config(config)
    if cfg.get("non_empty", "1") in {"1", "true", "yes"} and not _tokens(contestant_output):
        return _ret(1, err="empty output")
    return _ret(0)


def check_grid(input_data, contestant_output, expected_output, config=""):
    vals = _ints(input_data)
    if len(vals) < 2:
        return _ret(1, err="invalid input")
    n, m = vals[0], vals[1]
    rows = [ln.split() for ln in (contestant_output or "").strip().splitlines() if ln.strip()]
    if len(rows) != n:
        return _ret(1, err="row mismatch")
    if any(len(r) != m for r in rows):
        return _ret(1, err="col mismatch")
    cfg = parse_config(config)
    if "values" in cfg:
        allowed = set(x.strip() for x in cfg["values"].split("|" if "|" in cfg["values"] else ","))
        for r in rows:
            for x in r:
                if x not in allowed:
                    return _ret(1, err="value out of allowed set")
    return _ret(0)


def check_geometry(input_data, contestant_output, expected_output, config=""):
    cfg = parse_config(config)
    if "eps" in cfg:
        return check_numeric(input_data, contestant_output, expected_output, config)
    # fallback: order-insensitive token compare
    return check_set_compare(input_data, contestant_output, expected_output, config)


def check_tree(input_data, contestant_output, expected_output, config=""):
    vals = _ints(input_data)
    if not vals:
        return _ret(1, err="missing n")
    n = vals[0]
    out = _ints(contestant_output)
    if len(out) != 2 * (n - 1):
        return _ret(1, err="must output n-1 edges")
    parent = list(range(n + 1))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra == rb:
            return False
        parent[ra] = rb
        return True

    for i in range(0, len(out), 2):
        u, v = out[i], out[i + 1]
        if not (1 <= u <= n and 1 <= v <= n) or u == v:
            return _ret(1, err="invalid edge")
        if not union(u, v):
            return _ret(1, err="cycle detected")

    root = find(1)
    for x in range(2, n + 1):
        if find(x) != root:
            return _ret(1, err="graph not connected")
    return _ret(0)


CHECKERS = {
    "permutation": check_permutation,
    "set_compare": check_set_compare,
    "numeric_tolerance": check_numeric,
    "float_tolerance": check_numeric,
    "euler_path": check_euler,
    "graph_path": check_graph_path,
    "matching": check_matching,
    "constructive": check_constructive,
    "grid": check_grid,
    "geometry": check_geometry,
    "tree": check_tree,
}


def run_builtin_checker(checker_type, input_data, contestant_output, expected_output, config=""):
    start = time.perf_counter()
    checker = CHECKERS.get((checker_type or "").strip().lower())
    if not checker:
        res = _ret(3, err=f"Unknown checker: {checker_type}")
    else:
        try:
            res = checker(input_data, contestant_output, expected_output, config)
        except Exception as exc:
            res = _ret(3, err=f"Checker exception: {exc}")
    res["time"] = time.perf_counter() - start
    return res
