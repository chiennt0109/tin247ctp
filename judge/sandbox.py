from __future__ import annotations

import os
import shutil
import tempfile
from dataclasses import dataclass


@dataclass
class SandboxContext:
    submission_id: int
    root_dir: str


class SandboxManager:
    """Create isolated filesystem workspace for each submission."""

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or os.getenv("OJ_SANDBOX_ROOT", "/tmp/tin247ctp_sandbox")

    def create(self, submission_id: int) -> SandboxContext:
        os.makedirs(self.base_dir, exist_ok=True)
        root_dir = tempfile.mkdtemp(prefix=f"sub_{submission_id}_", dir=self.base_dir)
        return SandboxContext(submission_id=submission_id, root_dir=root_dir)

    def destroy(self, ctx: SandboxContext) -> None:
        shutil.rmtree(ctx.root_dir, ignore_errors=True)
