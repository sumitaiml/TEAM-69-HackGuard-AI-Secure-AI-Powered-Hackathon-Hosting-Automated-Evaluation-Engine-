import subprocess
import threading
import time
from typing import Any, Dict, List, Optional

import docker
from docker.errors import NotFound

from app.config import settings
from app.services.sandbox_profiles import detect_profile


def _sample_container_stats(container, samples: List[dict], stop_event: threading.Event, interval: float = 0.5) -> None:
    """Runs in a background thread for the lifetime of one container, since
    `docker stats` only reports meaningful (non-zero) usage for a container
    that is still running - polling once after `wait()` returns would just
    see an already-exited container. Stops silently on any error (container
    removed/exited mid-sample is the expected end condition, not a bug)."""
    while not stop_event.is_set():
        try:
            samples.append(container.stats(stream=False))
        except Exception:
            break
        stop_event.wait(interval)


def _compute_resource_usage(samples: List[dict]) -> Dict[str, float]:
    """Module 9: CPU Usage, Memory Usage - derived from sampled `docker stats`
    snapshots. CPU percent uses Docker's own standard formula (delta of
    container CPU usage over delta of system CPU usage, scaled by online
    CPU count) since the API only reports cumulative counters, not a
    ready-made percentage."""
    peak_memory_mb = 0.0
    cpu_percentages: List[float] = []
    for stats in samples:
        try:
            peak_memory_mb = max(peak_memory_mb, stats["memory_stats"]["usage"] / (1024 * 1024))
        except (KeyError, TypeError):
            pass
        try:
            cpu, precpu = stats["cpu_stats"], stats["precpu_stats"]
            cpu_delta = cpu["cpu_usage"]["total_usage"] - precpu["cpu_usage"]["total_usage"]
            system_delta = cpu["system_cpu_usage"] - precpu.get("system_cpu_usage", 0)
            online_cpus = cpu.get("online_cpus") or len(cpu["cpu_usage"].get("percpu_usage") or [1])
            if system_delta > 0 and cpu_delta > 0:
                cpu_percentages.append((cpu_delta / system_delta) * online_cpus * 100.0)
        except (KeyError, TypeError):
            pass
    return {
        "peak_memory_mb": round(peak_memory_mb, 2),
        "avg_cpu_percent": round(sum(cpu_percentages) / len(cpu_percentages), 2) if cpu_percentages else 0.0,
    }


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
    stats_samples: List[dict] = []
    stop_sampling = threading.Event()
    sampler_thread: Optional[threading.Thread] = None

    try:
        container = client.containers.run(**run_kwargs)
        sampler_thread = threading.Thread(
            target=_sample_container_stats, args=(container, stats_samples, stop_sampling), daemon=True
        )
        sampler_thread.start()
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
        stop_sampling.set()
        if sampler_thread is not None:
            sampler_thread.join(timeout=2)
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
        **_compute_resource_usage(stats_samples),
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
            "peak_memory_mb": install["peak_memory_mb"],
            "avg_cpu_percent": install["avg_cpu_percent"],
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
        # Module 9: measured from the test/run phase specifically (not install)
        # since that's the actual "Execute Application" step the PRD means by
        # these metrics - peak memory and average CPU% sampled while it ran.
        "peak_memory_mb": run["peak_memory_mb"],
        "avg_cpu_percent": run["avg_cpu_percent"],
    }
