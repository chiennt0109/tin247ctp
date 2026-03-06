from dataclasses import dataclass, field
from typing import List


@dataclass
class TestResult:
    test_id: int
    input_size: int
    execution_time: float
    program_exit_code: int
    checker_type: str
    checker_exit_code: int
    checker_stdout: str = ""
    checker_stderr: str = ""
    verdict: str = ""


@dataclass
class SubmissionResult:
    total_tests: int
    passed_tests: int = 0
    max_time: float = 0.0
    verdict: str = "Pending"
    tests: List[TestResult] = field(default_factory=list)

    def add(self, t: TestResult):
        self.tests.append(t)
        if t.verdict == "Accepted":
            self.passed_tests += 1
        self.max_time = max(self.max_time, t.execution_time)

    def finalize(self):
        if self.passed_tests == self.total_tests:
            self.verdict = "Accepted"
            return
        for t in self.tests:
            if t.verdict.startswith("Runtime Error"):
                self.verdict = "Runtime Error"
                return
            if t.verdict == "Time Limit Exceeded":
                self.verdict = "Time Limit Exceeded"
                return
            if t.verdict == "Memory Limit Exceeded":
                self.verdict = "Memory Limit Exceeded"
                return
            if t.verdict in ("Wrong Answer", "Presentation Error"):
                self.verdict = "Wrong Answer"
                return
            if t.verdict == "Checker Error":
                self.verdict = "Judge Error"
                return
        self.verdict = "Wrong Answer"
