import subprocess
import time
from typing import Any, Dict, Optional

import docker
from docker.errors import NotFound

from app.config import settings
from app.services.sandbox_profiles import detect_profile


def _get_client():
    return docker.from_env()


def _ensure_sandbox_network(client) -> None:
    """Idempotently creates the dedicated bridge network sandbox containers
    run on. Deliberately not compose-managed (see docker-compose.yml) so it
    can't accidentally end up attached to the app's internal network."""
    try:
        client.networks.get(settings.SANDBOX_NETWORK_NAME)
    except NotFound:
        client.networks.create(settings.SANDBOX_NETWORK_NAME, driver="bridge")


def _make_workspace_world_writable(project_root: str) -> None:
    """The worker (running as root) extracts submissions, so files land
    root-owned. The sandbox containers run as a fixed non-root uid (both
    install and test phases, for consistent ownership across the two) and
    need to read/write/execute the same directory - proper UID mapping is
    more machinery than this warrants, so the pragmatic fix is a permissive
    chmod scoped to just this one submission's own extracted directory."""
    subprocess.run(["chmod", "-R", "777", project_root], check=False)


def _run_phase(
    client,
    image: str,
    command,
    workdir: str,
    timeout: int,
    network_disabled: bool,
    network: Optional[str] = None,
    read_only: bool = False,
) -> Dict[str, Any]:
    """Runs one container to completion or until timeout. Always removes the
    container afterward regardless of outcome - `--rm`/auto_remove alone
    isn't reliable across the kill-on-timeout path, so cleanup happens
    explicitly in `finally`."""
    container = None
    start = time.time()
    run_kwargs: Dict[str, Any] = dict(
        image=image,
        command=command,
        working_dir=workdir,
        volumes={settings.SANDBOX_VOLUME_NAME: {"bind": "/workspace", "mode": "rw"}},
        mem_limit=settings.DOCKER_MEMORY_LIMIT,
        nano_cpus=int(settings.DOCKER_CPU_CAP * 1_000_000_000),
        pids_limit=settings.DOCKER_PIDS_LIMIT,
        user="1000:1000",
        detach=True,
        network_disabled=network_disabled,
    )
    if network:
        run_kwargs["network"] = network
    if read_only:
        run_kwargs["read_only"] = True
        run_kwargs["tmpfs"] = {"/tmp": "rw,size=64m"}
        run_kwargs["cap_drop"] = ["ALL"]
        run_kwargs["security_opt"] = ["no-new-privileges"]

    timed_out = False
    exit_code = -1
    logs = ""
    error: Optional[str] = None

    try:
        container = client.containers.run(**run_kwargs)
        try:
            result = container.wait(timeout=timeout)
            exit_code = result.get("StatusCode", -1)
        except Exception as wait_error:
            # Client-side abort on the wait() call - the container itself
            # keeps running until we kill it below. This is the real
            # timeout enforcement mechanism (there's no server-side deadline
            # option on `docker run` itself).
            timed_out = True
            error = f"execution exceeded {timeout}s timeout: {wait_error}"
            try:
                container.kill()
            except Exception:
                pass
        try:
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
        except Exception:
            pass
    except Exception as e:
        error = str(e)
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass

    return {
        "exit_code": exit_code,
        "logs": logs,
        "elapsed_seconds": round(time.time() - start, 2),
        "timed_out": timed_out,
        "error": error,
    }


def execute_in_docker_sandbox(submission_id: str, source_dir: Optional[str]) -> Dict[str, Any]:
    """Module 9: Isolated Secure Docker Sandbox Runner.

    Two phases, mapping the PRD's hardening spec to real container runs:
      1. Install (network on, dedicated sandbox network only - never the
         app's internal network) so dependency installation can reach the
         public internet without ever reaching postgres/redis/api/worker.
      2. Run/test (network fully disabled, read-only rootfs, non-root,
         all capabilities dropped) with a hard timeout.
    """
    if not settings.DOCKER_SANDBOX_ENABLED:
        return {"status": "skipped", "reason": "Docker sandbox disabled", "build_status": "SKIPPED"}

    if not source_dir:
        return {"status": "skipped", "reason": "No source code available to execute", "build_status": "SKIPPED"}

    profile, project_root = detect_profile(source_dir)
    if not profile:
        return {
            "status": "skipped",
            "reason": "No recognized build system (package.json / requirements.txt / pyproject.toml) found",
            "build_status": "SKIPPED",
        }

    _make_workspace_world_writable(project_root)

    execution_logs = [f"[INFO] Detected {profile['name']} project at {project_root}"]

    try:
        client = _get_client()
        _ensure_sandbox_network(client)
    except Exception as e:
        return {
            "status": "error",
            "reason": f"Could not reach Docker daemon: {e}",
            "build_status": "ERROR",
        }

    execution_logs.append(f"[BUILD] Install: {' '.join(profile['install_cmd'])}")
    install = _run_phase(
        client, profile["image"], profile["install_cmd"], project_root,
        timeout=settings.DOCKER_TIMEOUT_SECONDS,
        network_disabled=False, network=settings.SANDBOX_NETWORK_NAME,
        read_only=False,
    )
    execution_logs.extend(install["logs"].splitlines()[-50:])

    if install["timed_out"] or install["error"] or install["exit_code"] != 0:
        return {
            "status": "completed",
            "build_status": "TIMEOUT" if install["timed_out"] else "FAILED",
            "unit_tests_passed": 0,
            "unit_tests_failed": 0,
            "execution_time_seconds": install["elapsed_seconds"],
            "execution_logs": execution_logs,
            "error": install["error"] or f"install exited with code {install['exit_code']}",
        }

    execution_logs.append(f"[TEST] Run: {' '.join(profile['run_cmd'])}")
    run = _run_phase(
        client, profile["image"], profile["run_cmd"], project_root,
        timeout=settings.DOCKER_TIMEOUT_SECONDS,
        network_disabled=True,
        read_only=True,
    )
    execution_logs.extend(run["logs"].splitlines()[-50:])
    execution_logs.append(f"[CONTAINER] Execution finished (sandbox containers removed).")

    test_counts = profile["parse_output"](run["logs"])
    build_status = "TIMEOUT" if run["timed_out"] else ("SUCCESS" if run["exit_code"] == 0 else "FAILED")

    return {
        "status": "completed",
        "build_status": build_status,
        "unit_tests_passed": test_counts["passed"],
        "unit_tests_failed": test_counts["failed"],
        "execution_time_seconds": round(install["elapsed_seconds"] + run["elapsed_seconds"], 2),
        "execution_logs": execution_logs,
        "error": run["error"],
    }
