import random
from arena.games.robot_step import parse_move

def build_input():
    return build_input_teen()

def build_input_teen():
    x, y = 5, 5
    gx = random.randint(0, 9)
    gy = random.randint(0, 9)
    trap = random.choice(["U", "D", "L", "R"])
    energy = random.randint(0, 5)

    meta = {
        "gx": gx,
        "gy": gy,
        "trap": trap,
        "energy": energy,
    }

    return f"{x} {y} {gx} {gy} {trap} {energy}\n", meta

def judge(stdout, meta):
    return judge_teen(stdout, meta)

def judge_teen(stdout: str, meta: dict):
    mv = parse_move(stdout)

    if meta["energy"] <= 0:
        return (15 if mv == "STOP" else 0, "NO_ENERGY")

    dx = meta["gx"] - 5
    dy = meta["gy"] - 5

    if abs(dx) >= abs(dy):
        ideal = "UP" if dx < 0 else "DOWN" if dx > 0 else None
    else:
        ideal = "LEFT" if dy < 0 else "RIGHT" if dy > 0 else None

    if ideal == meta["trap"]:
        safe = ["UP", "DOWN", "LEFT", "RIGHT"]
        safe.remove(meta["trap"])
        return (15 if mv in safe else 0, "AVOID_TRAP")

    return (15 if mv == ideal else 0, "GOAL_MOVE")
