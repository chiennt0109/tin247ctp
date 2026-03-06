from dataclasses import dataclass, field
from typing import List


@dataclass
class TestResult:
    test_id: int
    execution_time: float
    memory_kb: int
    program_exit_code: int
    checker_exit_code: int
    verdict: str
    stdout: str = ""
    stderr: str = ""


@dataclass
class SubmissionResult:
    total_tests: int
    passed_tests: int = 0
    max_time: float = 0.0
    max_memory_kb: int = 0
    verdict: str = "JE"
    tests: List[TestResult] = field(default_factory=list)

    def add(self, test_result: TestResult) -> None:
        self.tests.append(test_result)
        if test_result.verdict == "AC":
            self.passed_tests += 1
        self.max_time = max(self.max_time, test_result.execution_time)
        self.max_memory_kb = max(self.max_memory_kb, test_result.memory_kb)

    def finalize(self) -> None:
        if self.total_tests == 0:
            self.verdict = "JE"
            return
        if self.passed_tests == self.total_tests:
            self.verdict = "AC"
            return
        for t in self.tests:
            if t.verdict != "AC":
                self.verdict = t.verdict
                return
        self.verdict = "WA"

    def to_payload(self) -> dict:
        return {
            "verdict": self.verdict,
            "time": round(self.max_time, 3),
            "memory": int(self.max_memory_kb),
            "passed": int(self.passed_tests),
            "total": int(self.total_tests),
        }


VERDICT_TO_DB = {
    "AC": "Accepted",
    "WA": "Wrong Answer",
    "TLE": "Time Limit Exceeded",
    "MLE": "Runtime Error",
    "RE": "Runtime Error",
    "CE": "Compilation Error",
    "PE": "Wrong Answer",
    "JE": "Judge Error",
}
