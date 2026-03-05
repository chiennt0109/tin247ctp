from __future__ import annotations

from collections import Counter
from typing import Iterable, List, Sequence, Tuple


def tokens(text: str) -> List[str]:
    return (text or "").split()


def read_ints(text: str) -> List[int]:
    return [int(x) for x in tokens(text)]


def read_matrix(text: str, rows: int, cols: int) -> List[List[int]]:
    vals = read_ints(text)
    if len(vals) != rows * cols:
        raise ValueError("invalid matrix size")
    return [vals[i * cols:(i + 1) * cols] for i in range(rows)]


def verify_permutation(seq: Sequence[int], n: int) -> bool:
    return len(seq) == n and set(seq) == set(range(1, n + 1))


def verify_graph_path(path: Sequence[int], edges: Iterable[Tuple[int, int]], directed: bool = False) -> bool:
    if not path:
        return False
    edge_set = set(edges)
    if not directed:
        edge_set |= {(v, u) for (u, v) in edge_set}
    return all((path[i], path[i + 1]) in edge_set for i in range(len(path) - 1))


def verify_matching(pairs: Sequence[Tuple[int, int]], edges: Iterable[Tuple[int, int]]) -> bool:
    edge_set = set(edges)
    left = Counter(a for a, _ in pairs)
    right = Counter(b for _, b in pairs)
    return (
        all(c == 1 for c in left.values())
        and all(c == 1 for c in right.values())
        and all((a, b) in edge_set for a, b in pairs)
    )
