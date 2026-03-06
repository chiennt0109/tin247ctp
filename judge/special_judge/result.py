from dataclasses import dataclass, asdict


@dataclass
class SpecialJudgeResult:
    return_code: int
    stdout: str = ""
    stderr: str = ""
    time: float = 0.0
    mode: str = ""

    def to_dict(self):
        return asdict(self)
