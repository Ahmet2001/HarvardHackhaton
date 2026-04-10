from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    ok: bool
    returncode: int | None
    stdout: str
    stderr: str
    command: list[str]


def binary_exists(binary: str) -> bool:
    return shutil.which(binary) is not None


def run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout_seconds: int = 900,
) -> CommandResult:
    try:
        process = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except FileNotFoundError as exc:
        return CommandResult(False, None, "", str(exc), command)
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            False,
            None,
            exc.stdout or "",
            f"Command timed out after {timeout_seconds}s. {exc.stderr or ''}".strip(),
            command,
        )

    return CommandResult(
        process.returncode == 0,
        process.returncode,
        process.stdout,
        process.stderr,
        command,
    )

