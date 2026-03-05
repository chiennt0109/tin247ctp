# arena/games/snake.py
import json
from dataclasses import dataclass
from typing import List, Dict, Tuple

DEFAULT_MAP = [
    "S....#....",
    ".##....F..",
    "..........",
    "..F.......",
    ".....#....",
    "....F.....",
    "..........",
    "....#.....",
    "..F.......",
    "......F..."
]

MAX_TURNS = 40

DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "UP": (-1, 0),
    "DOWN": (1, 0),
    "LEFT": (0, -1),
    "RIGHT": (0, 1),
}


@dataclass
class SnakeResult:
    score: int
    steps: int
    status: str
    frames: List[List[str]]
    error: str = ""


def build_input_for_bot() -> str:
    """
    Sinh input cho bot:
      H W T
      <H dòng lưới>
    """
    H = len(DEFAULT_MAP)
    W = len(DEFAULT_MAP[0])
    lines = [f"{H} {W} {MAX_TURNS}"]
    lines.extend(DEFAULT_MAP)
    return "\n".join(lines) + "\n"


def parse_moves(raw_output: str) -> List[str]:
    moves: List[str] = []
    for line in raw_output.strip().splitlines():
        mv = line.strip().upper()
        if mv in DIRECTIONS:
            moves.append(mv)
        if len(moves) >= MAX_TURNS:
            break
    return moves


def simulate_snake(moves: List[str]) -> SnakeResult:
    grid = [list(row) for row in DEFAULT_MAP]
    H = len(grid)
    W = len(grid[0])

    # tìm 'S'
    sx = sy = None
    for i in range(H):
        for j in range(W):
            if grid[i][j] == "S":
                sx, sy = i, j
                break
        if sx is not None:
            break

    if sx is None:
        return SnakeResult(0, 0, "INVALID_MAP", [DEFAULT_MAP], error="Không tìm thấy S trong map")

    x, y = sx, sy
    score = 0
    frames: List[List[str]] = []

    def snapshot() -> List[str]:
        tmp = [row[:] for row in grid]
        tmp[x][y] = "R"
        return ["".join(r) for r in tmp]

    frames.append(snapshot())

    for step, mv in enumerate(moves, start=1):
        dx, dy = DIRECTIONS[mv]
        nx, ny = x + dx, y + dy

        if nx < 0 or nx >= H or ny < 0 or ny >= W:
            return SnakeResult(score, step - 1, "OUT_OF_BOUND", frames)

        cell = grid[nx][ny]
        if cell == "#":
            return SnakeResult(score, step - 1, "HIT_WALL", frames)
        if cell == "F":
            score += 10
            grid[nx][ny] = "."

        x, y = nx, ny
        frames.append(snapshot())

    status = "OK" if moves else "NO_MOVE"
    return SnakeResult(score, len(moves), status, frames)


def result_to_json(result: SnakeResult) -> str:
    payload = {
        "score": result.score,
        "steps": result.steps,
        "status": result.status,
        "frames": result.frames,
        "error": result.error,
    }
    return json.dumps(payload, ensure_ascii=False)
