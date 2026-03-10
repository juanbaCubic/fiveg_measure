"""
fiveg_measure/utils/subprocess_runner.py — Safe subprocess wrapper.
"""
from __future__ import annotations

import logging
import subprocess
from typing import Optional

log = logging.getLogger(__name__)


class SubprocessResult:
    def __init__(self, returncode: int, stdout: str, stderr: str, cmd: list[str]):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.cmd = cmd
        self.ok = returncode == 0

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SubprocessResult rc={self.returncode} cmd={self.cmd}>"


def run_cmd(
    cmd: list[str],
    timeout: float = 300,
    input_data: Optional[str] = None,
    env: Optional[dict] = None,
) -> SubprocessResult:
    """Run a subprocess, capture stdout/stderr, never raise on non-zero exit."""
    log.debug("Running: %s", " ".join(str(c) for c in cmd))
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            input=input_data,
            env=env,
        )
        result = SubprocessResult(proc.returncode, proc.stdout, proc.stderr, cmd)
    except subprocess.TimeoutExpired:
        log.warning("Command timed out after %ss: %s", timeout, cmd)
        result = SubprocessResult(-1, "", "TIMEOUT", cmd)
    except FileNotFoundError:
        log.error("Command not found: %s", cmd[0])
        result = SubprocessResult(-1, "", f"NOT_FOUND: {cmd[0]}", cmd)
    except Exception as exc:  # noqa: BLE001
        log.error("Unexpected error running %s: %s", cmd, exc)
        result = SubprocessResult(-1, "", str(exc), cmd)
    if not result.ok and result.stderr:
        log.debug("stderr: %s", result.stderr[:500])
    return result
