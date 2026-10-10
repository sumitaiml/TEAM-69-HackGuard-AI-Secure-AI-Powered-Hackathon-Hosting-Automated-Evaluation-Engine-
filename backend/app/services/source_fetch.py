import os
import shutil
import subprocess
import zipfile
from typing import Optional

from app import models
from app.config import settings


class SourceFetchError(Exception):
    pass


def safe_extract_zip(zip_path: str, dest_dir: str) -> str:
    """Extracts a zip archive into dest_dir, rejecting any entry whose
    resolved path would escape dest_dir (zip-slip: '..', absolute paths,
    or symlink-like tricks in the entry name)."""
    os.makedirs(dest_dir, exist_ok=True)
    dest_real = os.path.realpath(dest_dir)

    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.infolist():
            member_path = os.path.realpath(os.path.join(dest_dir, member.filename))
            if member_path != dest_real and not member_path.startswith(dest_real + os.sep):
                raise SourceFetchError(f"Unsafe path in zip archive: {member.filename}")
        zf.extractall(dest_dir)

    return dest_dir


def clone_repo(url: str, dest_dir: str, timeout: int = 30) -> str:
    if not url.startswith("https://"):
        raise SourceFetchError("Only https:// repository URLs are supported")
    os.makedirs(dest_dir, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", url, dest_dir],
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise SourceFetchError(f"git clone failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise SourceFetchError("git clone timed out")
    return dest_dir


def clone_repo_with_history(url: str, dest_dir: str, timeout: int = 60) -> str:
    """Used only by the timeline/anti-cheating agent - clone_repo()'s
    --depth 1 discards commit history entirely, which that agent needs to
    read. --depth 200 is a deliberate bound (not a full clone): comfortably
    covers any realistic hackathon project's history while still keeping
    clone time bounded for a pathological repo with years of history."""
    if not url.startswith("https://"):
        raise SourceFetchError("Only https:// repository URLs are supported")
    os.makedirs(dest_dir, exist_ok=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth", "200", url, dest_dir],
            check=True,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        raise SourceFetchError(f"git clone (with history) failed: {e.stderr}")
    except subprocess.TimeoutExpired:
        raise SourceFetchError("git clone (with history) timed out")
    return dest_dir


def extract_submission_source(submission: "models.Submission") -> Optional[str]:
    """Returns a local directory containing the submission's source code,
    extracting/cloning it on first use and reusing the cached copy on
    subsequent calls within the same evaluation pipeline. Both the API
    process and the Celery worker share this path via the sandbox_workspace
    volume, so Phase 5's sandbox execution reuses whatever was extracted
    here instead of fetching the source a second time.

    Returns None if the submission has neither an uploaded zip nor a repo
    URL - callers must handle "nothing to analyze" explicitly.
    """
    src_dir = os.path.join(settings.WORKSPACE_ROOT, submission.id, "src")

    if os.path.isdir(src_dir) and os.listdir(src_dir):
        return src_dir

    if submission.zip_path and os.path.exists(submission.zip_path):
        safe_extract_zip(submission.zip_path, src_dir)
        return src_dir

    if submission.github_url:
        try:
            clone_repo(submission.github_url, src_dir)
            return src_dir
        except SourceFetchError:
            shutil.rmtree(src_dir, ignore_errors=True)
            return None

    return None
