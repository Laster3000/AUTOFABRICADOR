"""Fail-closed Docker Linux execution. The factory never runs model code on host."""
from __future__ import annotations
import os
from pathlib import Path
import hashlib
import re
import shutil
import subprocess
import sys
import time

class IsolationUnavailable(RuntimeError):
    pass

def docker_preflight(image="python:3.12-slim"):
    docker = shutil.which("docker")
    if not docker:
        raise IsolationUnavailable("DOCKER_NOT_INSTALLED")
    try:
        info = subprocess.run([docker,"info","--format","{{.OSType}}"],capture_output=True,text=True,timeout=12)
        if info.returncode or info.stdout.strip() != "linux":
            raise IsolationUnavailable("DOCKER_LINUX_DAEMON_UNAVAILABLE")
        inspect = subprocess.run([docker,"image","inspect","--format","{{.Id}}",image],capture_output=True,text=True,timeout=12)
        if inspect.returncode or not re.fullmatch(r"sha256:[0-9a-f]{64}",inspect.stdout.strip()):
            raise IsolationUnavailable("REQUIRED_DOCKER_IMAGE_NOT_INSTALLED_OR_NO_SHA256_ID")
    except subprocess.TimeoutExpired as e:
        raise IsolationUnavailable("DOCKER_PREFLIGHT_TIMEOUT") from e
    return docker, inspect.stdout.strip()

def run_tests(work: Path, *, timeout=60, image="python:3.12-slim", max_output=18000):
    docker, image_id = docker_preflight(image)
    work = Path(work).resolve()
    if not work.is_dir():
        raise IsolationUnavailable("WORKSPACE_MISSING")
    # Only the candidate source tree is mounted; read only. No network or root privileges.
    command = [
        docker,"run","--rm","--name","af-"+hashlib.sha256(str(work).encode()).hexdigest()[:16],"--pull=never","--network","none","--read-only",
        "--cap-drop","ALL","--security-opt","no-new-privileges",
        "--pids-limit","64","--memory","384m","--cpus","1",
        "--user","65534:65534","--tmpfs","/tmp:rw,noexec,nosuid,size=32m",
        "--mount",f"type=bind,source={work},target=/workspace,readonly",
        "--workdir","/workspace","--env","PYTHONDONTWRITEBYTECODE=1",
        image_id,"python","-m","unittest","discover","-s","/workspace","-p","test_*.py","-v"
    ]
    start=time.monotonic()
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=timeout, check=False)
    except subprocess.TimeoutExpired as error:
        # Docker CLI timeout may leave a container running. Caller marks UNKNOWN; no blind replay.
        raise IsolationUnavailable("DOCKER_OPERATION_TIMEOUT_UNKNOWN_RECONCILE") from error
    stdout=result.stdout[:max_output].decode("utf-8","replace")
    stderr=result.stderr[:max_output].decode("utf-8","replace")
    counts=re.findall(r"(?m)^Ran (\d+) tests? in ",stderr)
    executed=int(counts[-1]) if counts else 0
    return {
        "exitCode":result.returncode if executed>=1 else -7,
        "testCount":executed,
        "stdout":stdout,
        "stderr":stderr,
        "durationMs":round((time.monotonic()-start)*1000),
        "backend":"docker-linux-network-none-readonly", "imageId":image_id,
        "failureReason":"ZERO_TESTS_OR_MISSING_UNSUPPORTED_OUTPUT" if executed==0 else None
    }
