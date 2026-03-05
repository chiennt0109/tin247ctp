import random
from arena.games.robot_step import parse_move

def build_input():
    return build_input_chick()

def build_input_chick():
    task = random.choice([1, 2, 3])

    if task == 1:
        N = random.randint(1, 5)
        return f"{N}\n", {"task": 1, "N": N}

    if task == 2:
        dx = random.randint(-3, 3)
        dy = random.randint(-3, 3)
        return f"{dx} {dy}\n", {"task": 2, "dx": dx, "dy": dy}

    if task == 3:
        r = round(random.uniform(1, 5), 1)
        return f"{r}\n", {"task": 3, "r": r}

def judge(stdout, meta):
    return judge_chick(stdout, meta)

def judge_chick(stdout: str, meta: dict):
    move_tokens = stdout.strip().split()

    if meta["task"] == 1:
        return (15, "OK") if move_tokens == ["UP"] * meta["N"] else (0, "WRONG")

    if meta["task"] == 2:
        correct = []
        dx, dy = meta["dx"], meta["dy"]

        if dx < 0: correct += ["UP"] * abs(dx)
        elif dx > 0: correct += ["DOWN"] * dx

        if dy < 0: correct += ["LEFT"] * abs(dy)
        elif dy > 0: correct += ["RIGHT"] * dy

        return (15, "OK") if move_tokens == correct else (0, "WRONG")

    if meta["task"] == 3:
        expected = 2 * 3.1415926535 * meta["r"]
        try:
            out = float(stdout.strip())
            return (15, "OK") if abs(out - expected) < 0.02 else (0, "WRONG")
        except:
            return (0, "WRONG")

    return (0, "INVALID")
