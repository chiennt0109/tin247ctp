import json, random
from dataclasses import dataclass

DIRECTIONS = {
    "U": "UP",
    "D": "DOWN",
    "L": "LEFT",
    "R": "RIGHT"
}

def build_input():
    secret = random.choice(["U", "D", "L", "R"])
    return secret, secret + "\n"

def build_input_egg():
    return build_input()

def parse_move(out):
    if not out:
        return ""
    return out.strip().split()[0].upper()

@dataclass
class ResultEgg:
    score: int
    status: str
    secret: str
    bot: str
    error: str = ""

def judge(secret, bot):
    if bot not in ["UP", "DOWN", "LEFT", "RIGHT"]:
        return ResultEgg(score=0, status="INVALID", secret=secret, bot=bot, error="Bot in không hợp lệ")
    score = 10
    if DIRECTIONS[secret] == bot:
        score += 5
    return ResultEgg(score=score, status="OK", secret=secret, bot=bot)

def judge_egg(secret, bot):
    return judge(secret, bot)

def to_json(r: ResultEgg):
    return json.dumps({
        "score": r.score,
        "status": r.status,
        "secret": r.secret,
        "bot": r.bot,
        "error": r.error,
        "before": [], "after": []
    })

def simulate_robot_from_position(secret, move, x, y):
    before = generate_grid_with_robot_at(x, y)

    if move not in DIRECTIONS:
        return before, before, x, y, 0, "INVALID"

    dx, dy = DIRECTIONS[move]
    nx, ny = x + dx, y + dy

    # vượt biên → đứng yên
    if not (0 <= nx < GRID_SIZE and 0 <= ny < GRID_SIZE):
        return before, before, x, y, 0, "OUT"

    after = generate_grid_with_robot_at(nx, ny)

    score = 10 + (5 if move[0] == secret else 0)

    return before, after, nx, ny, score, "OK"
