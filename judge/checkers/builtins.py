from __future__ import annotations

import math
from typing import Callable, Dict, List, Tuple

from .utils import read_ints, tokens, verify_graph_path, verify_matching, verify_permutation

RC_ACCEPTED = 0
RC_WRONG_ANSWER = 1
RC_PRESENTATION = 2


def _ok(msg: str = "OK"):
    return RC_ACCEPTED, msg


def _wa(msg: str):
    return RC_WRONG_ANSWER, msg


def _pe(msg: str):
    return RC_PRESENTATION, msg


def checker_euler_path(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    ints = read_ints(input_file)
    if len(ints) < 2:
        return _wa("Invalid input format")
    n, m = ints[0], ints[1]
    flat = ints[2:]
    if len(flat) < 2 * m:
        return _wa("Not enough edges")
    edges = [(flat[2 * i], flat[2 * i + 1]) for i in range(m)]
    path = read_ints(contestant_output)
    if len(path) != m + 1:
        return _wa("Path length must be m+1")
    # multiset edge use check (undirected)
    edge_count = {}
    for u, v in edges:
        k = (min(u, v), max(u, v))
        edge_count[k] = edge_count.get(k, 0) + 1
    for i in range(m):
        u, v = path[i], path[i + 1]
        k = (min(u, v), max(u, v))
        if edge_count.get(k, 0) <= 0:
            return _wa("Edge used invalid or too many times")
        edge_count[k] -= 1
    if any(v != 0 for v in edge_count.values()):
        return _wa("Not all edges are used")
    if any(x < 1 or x > n for x in path):
        return _wa("Vertex out of range")
    return _ok()


def checker_graph_path(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    ints = read_ints(input_file)
    if len(ints) < 2:
        return _wa("Invalid input format")
    n, m = ints[0], ints[1]
    flat = ints[2:]
    if len(flat) < 2 * m:
        return _wa("Not enough edges")
    edges = [(flat[2 * i], flat[2 * i + 1]) for i in range(m)]
    path = read_ints(contestant_output)
    if not path:
        return _pe("Empty output")
    if any(x < 1 or x > n for x in path):
        return _wa("Vertex out of range")
    if not verify_graph_path(path, edges, directed=False):
        return _wa("Invalid edge in path")
    return _ok()


def checker_permutation(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    ints = read_ints(input_file)
    if not ints:
        return _wa("Missing n")
    n = ints[0]
    p = read_ints(contestant_output)
    if verify_permutation(p, n):
        return _ok()
    return _wa("Output is not a permutation of 1..n")


def checker_permutation_constraints(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    # Generic: must be permutation. Optional config: increasing_prefix=k
    ints = read_ints(input_file)
    if not ints:
        return _wa("Missing n")
    n = ints[0]
    p = read_ints(contestant_output)
    if not verify_permutation(p, n):
        return _wa("Invalid permutation")
    if config.startswith("increasing_prefix="):
        k = int(config.split("=", 1)[1])
        if p[:k] != sorted(p[:k]):
            return _wa("Constraint increasing_prefix violated")
    return _ok()


def checker_matching(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    ints = read_ints(input_file)
    if len(ints) < 3:
        return _wa("Invalid input")
    n_left, n_right, m = ints[0], ints[1], ints[2]
    flat = ints[3:]
    if len(flat) < 2 * m:
        return _wa("Not enough edges")
    edges = [(flat[2 * i], flat[2 * i + 1]) for i in range(m)]
    out = read_ints(contestant_output)
    if len(out) % 2:
        return _wa("Matching output must have even number of ints")
    pairs = [(out[i], out[i + 1]) for i in range(0, len(out), 2)]
    if any(a < 1 or a > n_left for a, _ in pairs) or any(b < 1 or b > n_right for _, b in pairs):
        return _wa("Vertex out of range")
    if not verify_matching(pairs, edges):
        return _wa("Invalid matching")
    return _ok()


def checker_assignment(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    ints = read_ints(input_file)
    if len(ints) < 2:
        return _wa("Invalid input")
    workers, tasks = ints[0], ints[1]
    out = read_ints(contestant_output)
    if len(out) != workers:
        return _wa("Need exactly one task per worker")
    if any(x < 1 or x > tasks for x in out):
        return _wa("Task id out of range")
    cap = 1
    if config.startswith("capacity="):
        cap = int(config.split("=", 1)[1])
    used = {}
    for t in out:
        used[t] = used.get(t, 0) + 1
        if used[t] > cap:
            return _wa("Task capacity exceeded")
    return _ok()


def checker_constructive(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    # Generic fallback: accept any non-empty output unless explicit impossible marker in expected.
    out = tokens(contestant_output)
    exp = tokens(expected_output)
    if exp and exp[0] == "IMPOSSIBLE":
        return _ok() if (out and out[0] == "IMPOSSIBLE") else _wa("Must output IMPOSSIBLE")
    return _ok() if out else _wa("Empty construction")


def checker_grid(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    ints = read_ints(input_file)
    if len(ints) < 2:
        return _wa("Invalid input")
    r, c = ints[0], ints[1]
    lines = [ln.strip() for ln in (contestant_output or "").strip().splitlines() if ln.strip()]
    if len(lines) != r:
        return _wa("Row count mismatch")
    grid = [ln.split() for ln in lines]
    if any(len(row) != c for row in grid):
        return _wa("Column count mismatch")
    return _ok()


def checker_set_compare(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    c = sorted(tokens(contestant_output))
    e = sorted(tokens(expected_output))
    return _ok() if c == e else _wa("Output differs as set")


def checker_numeric_tolerance(input_file: str, contestant_output: str, expected_output: str, config: str = ""):
    eps = 1e-6
    if config.startswith("eps="):
        eps = float(config.split("=", 1)[1])
    c = [float(x) for x in tokens(contestant_output)]
    e = [float(x) for x in tokens(expected_output)]
    if len(c) != len(e):
        return _wa("Token count mismatch")
    for a, b in zip(c, e):
        if math.fabs(a - b) > eps:
            return _wa(f"Difference {abs(a-b)} exceeds eps={eps}")
    return _ok()


BUILTIN_CHECKERS: Dict[str, Callable[[str, str, str, str], Tuple[int, str]]] = {
    "euler_path": checker_euler_path,
    "graph_path": checker_graph_path,
    "permutation": checker_permutation,
    "permutation_constraints": checker_permutation_constraints,
    "matching": checker_matching,
    "assignment": checker_assignment,
    "constructive": checker_constructive,
    "grid": checker_grid,
    "set_compare": checker_set_compare,
    "numeric_tolerance": checker_numeric_tolerance,
}
