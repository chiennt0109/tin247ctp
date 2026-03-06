from __future__ import annotations


def map_program_exit_code(returncode: int) -> str:
    if returncode == 0:
        return "OK"
    if returncode == 124:
        return "Time Limit Exceeded"
    if returncode == 137:
        return "Memory Limit Exceeded"
    if returncode in (139, -11):
        return "Runtime Error (Segmentation Fault)"
    if returncode == 134:
        return "Runtime Error (Abort)"
    return "Runtime Error"


def map_checker_exit_code(returncode: int) -> str:
    if returncode == 0:
        return "Accepted"
    if returncode == 2:
        return "Presentation Error"
    if returncode == 1:
        return "Wrong Answer"
    return "Checker Error"
