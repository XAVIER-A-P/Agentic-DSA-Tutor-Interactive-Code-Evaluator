
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time

from pathlib import Path


def execute_python(
    code: str,
    stdin: str = "",
) -> dict:

    """
    Execute Python inside a disposable Docker container.

    Requires Docker Desktop and the configured runner image.

    This is a local-development security baseline,
    not a production-grade hostile-code sandbox.
    """

    if not isinstance(code, str) or not code.strip():

        return {
            "status": "Invalid Submission",
            "stdout": "",
            "stderr": "No Python code was supplied.",
            "return_code": None,
            "execution_time_ms": 0.0,
        }

    max_code_chars = int(
        os.getenv("DSA_MAX_CODE_CHARS", "50000")
    )

    if len(code) > max_code_chars:

        return {
            "status": "Invalid Submission",
            "stdout": "",
            "stderr": (
                f"Code exceeds the {max_code_chars}-character limit."
            ),
            "return_code": None,
            "execution_time_ms": 0.0,
        }

    docker = shutil.which("docker")

    if not docker:

        return {
            "status": "Execution Environment Error",
            "stdout": "",
            "stderr": (
                "Docker was not found. "
                "Install and start Docker Desktop."
            ),
            "return_code": None,
            "execution_time_ms": 0.0,
        }

    image = os.getenv(
        "DSA_RUNNER_IMAGE",
        "python:3.11-slim",
    )

    timeout_seconds = max(
        1,
        int(os.getenv("DSA_EXECUTION_TIMEOUT", "5")),
    )

    with tempfile.TemporaryDirectory(
        prefix="dsa-run-"
    ) as temp_dir:

        workdir = Path(temp_dir)

        script = workdir / "main.py"

        script.write_text(
            code,
            encoding="utf-8",
        )

        command = [
            docker,
            "run",
            "--rm",
            "-i",
            "--network", "none",
            "--read-only",
            "--memory", "128m",
            "--memory-swap", "128m",
            "--cpus", "0.50",
            "--pids-limit", "64",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges",
            "--user", "65534:65534",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
            "-v", f"{workdir}:/workspace:ro",
            "-w", "/workspace",
            image,
            "python",
            "-I",
            "/workspace/main.py",
        ]

        started = time.perf_counter()

        try:

            completed = subprocess.run(
                command,
                input=stdin or "",
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
            )

        except subprocess.TimeoutExpired as exc:

            elapsed = (
                time.perf_counter() - started
            ) * 1000

            def decode(value):
                if isinstance(value, bytes):
                    return value.decode(
                        "utf-8",
                        errors="replace",
                    )

                return value or ""

            return {
                "status": "Time Limit Exceeded",
                "stdout": decode(exc.stdout)[-12000:],
                "stderr": decode(exc.stderr)[-12000:],
                "return_code": None,
                "execution_time_ms": round(elapsed, 2),
            }

        except OSError as exc:

            return {
                "status": "Execution Environment Error",
                "stdout": "",
                "stderr": str(exc),
                "return_code": None,
                "execution_time_ms": 0.0,
            }

        elapsed = (
            time.perf_counter() - started
        ) * 1000

        stdout = (completed.stdout or "")[-12000:]
        stderr = (completed.stderr or "")[-12000:]

        if completed.returncode == 0:

            status = "Accepted"

        elif (
            "Unable to find image" in stderr
            or "pull access denied" in stderr
        ):

            status = "Execution Environment Error"

        else:

            status = "Runtime Error"

        return {
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": completed.returncode,
            "execution_time_ms": round(elapsed, 2),
        }
