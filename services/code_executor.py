from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path


def execute_python(code: str, stdin: str = "") -> dict:
    """
    Execute Python in a disposable Docker container.

    Requires Docker Engine and the image configured by DSA_RUNNER_IMAGE.
    This is a practical baseline, not a substitute for a dedicated hostile-code
    sandbox such as gVisor/Firecracker in a public multi-tenant deployment.
    """
    image = os.getenv("DSA_RUNNER_IMAGE", "python:3.11-slim")
    timeout_seconds = int(os.getenv("DSA_EXECUTION_TIMEOUT", "5"))

    if not shutil_which("docker"):
        raise RuntimeError("Docker was not found. Install and start Docker Desktop.")

    with tempfile.TemporaryDirectory(prefix="dsa-run-") as tmp:
        workdir = Path(tmp)
        (workdir / "main.py").write_text(code, encoding="utf-8")
        start = time.perf_counter()

        command = [
            "docker", "run", "--rm", "-i",
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
            "python", "-I", "/workspace/main.py",
        ]

        try:
            completed = subprocess.run(
                command,
                input=stdin,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "status": "Time Limit Exceeded",
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "return_code": None,
                "execution_time_ms": round(timeout_seconds * 1000, 2),
            }

        elapsed = (time.perf_counter() - start) * 1000
        stdout = (completed.stdout or "")[-12000:]
        stderr = (completed.stderr or "")[-12000:]
        return {
            "status": "Accepted" if completed.returncode == 0 else "Runtime Error",
            "stdout": stdout,
            "stderr": stderr,
            "return_code": completed.returncode,
            "execution_time_ms": round(elapsed, 2),
        }


def shutil_which(command: str) -> str | None:
    # Avoid importing a broad helper just for one lookup.
    import shutil
    return shutil.which(command)
