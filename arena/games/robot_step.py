import json
import random
from dataclasses import dataclass
from typing import List

GRID_SIZE = 10

DIRECTIONS = {
    "U": (-1, 0), "UP": (-1, 0),
    "D": (1, 0),  "DOWN": (1, 0),
    "L": (0, -1), "LEFT": (0, -1),
    "R": (0, 1),  "RIGHT": (0, 1),
}

def random_secret():
    return random.choice(["U", "D", "L", "R"])

def build_input(secret: str):
    return secret + "\n"


def generate_grid_with_robot_at(x, y):
    grid = []
    for r in range(GRID_SIZE):
        row = ""
        for c in range(GRID_SIZE):
            row += "R" if (r == x and c == y) else "."
        grid.append(row)
    return grid


def parse_move(output: str) -> str:
    if not output:
        return ""
    return output.strip().split()[0].upper()


@dataclass
class StatefulRobotResult:
    before: List[str]
    after: List[str]
    new_x: int
    new_y: int
    score: int
    status: str
    secret: str
    bot_move: str
    error: str = ""


def simulate_robot_stateful(secret: str, move: str, x: int, y: int) -> StatefulRobotResult:
    before = generate_grid_with_robot_at(x, y)

    if move not in DIRECTIONS:
        return StatefulRobotResult(
            before, before,
            x, y,
            0, "INVALID",
            secret, move,
            "Lệnh bot không hợp lệ"
        )

    dx, dy = DIRECTIONS[move]
    nx, ny = x + dx, y + dy

    if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
        return StatefulRobotResult(
            before, before,
            x, y,
            0, "OUT_OF_BOUND",
            secret, move,
            "Robot đi ra ngoài bản đồ"
        )

    after = generate_grid_with_robot_at(nx, ny)

    # scoring
    score = 10
    if move[0] == secret:
        score += 5

    return StatefulRobotResult(
        before=before,
        after=after,
        new_x=nx,
        new_y=ny,
        score=score,
        status="OK",
        secret=secret,
        bot_move=move
    )


def result_to_json(r: StatefulRobotResult):
    return json.dumps({
        "before": r.before,
        "after": r.after,
        "new_x": r.new_x,
        "new_y": r.new_y,
        "score": r.score,
        "status": r.status,
        "secret": r.secret,
        "bot_move": r.bot_move,
        "error": r.error,
    }, ensure_ascii=False)
