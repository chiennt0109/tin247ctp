from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SandboxContext:
    submission_id: int
    container_id: str


class SandboxManager:
    """
    One sandbox context per submission.
    In local mode this is a lightweight abstraction. In production it can map to Docker/nsjail.
    """

    def create(self, submission_id: int) -> SandboxContext:
        return SandboxContext(submission_id=submission_id, container_id=f"local-{submission_id}")

    def destroy(self, _ctx: SandboxContext) -> None:
        return
