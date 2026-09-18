import os
import subprocess
import zipfile
from typing import Set

from fastapi import HTTPException, UploadFile

from app.config import settings

ALLOWED_ZIP_EXTENSIONS: Set[str] = {".zip"}
# Legacy binary .ppt (OLE2) is intentionally not accepted: python-pptx (used
# later for real PPT parsing) only reads the .pptx Office Open XML format.
ALLOWED_PPT_EXTENSIONS: Set[str] = {".pptx"}
ALLOWED_VIDEO_EXTENSIONS: Set[str] = {".mp4", ".mov", ".webm", ".avi", ".mkv"}

_CHUNK_SIZE = 1024 * 1024  # 1MB


def validate_extension(filename: str, allowed: Set[str], field_name: str) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail=f"{field_name}: filename is required")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"{field_name}: unsupported file type '{ext or 'unknown'}'. Allowed: {', '.join(sorted(allowed))}"
        )
    return ext


def save_upload_streamed(upload_file: UploadFile, dest_path: str, max_size_mb: int, field_name: str) -> int:
    """Streams an UploadFile to a fixed destination path, aborting (and
    removing the partial file) if it exceeds max_size_mb before ever holding
    the whole file in memory. Returns the total bytes written."""
    max_bytes = max_size_mb * 1024 * 1024
    total = 0
    try:
        with open(dest_path, "wb") as buffer:
            while True:
                chunk = upload_file.file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                total += len(chunk)
                if total > max_bytes:
                    raise HTTPException(
                        status_code=400,
                        detail=f"{field_name}: file exceeds the {max_size_mb}MB size limit"
                    )
                buffer.write(chunk)
    except HTTPException:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise
    return total


def validate_zip_structure(path: str, field_name: str) -> None:
    """.zip and .pptx are both zip containers, so this same structural check
    covers both without needing python-pptx just to sanity-check the upload."""
    if not zipfile.is_zipfile(path):
        os.remove(path)
        raise HTTPException(status_code=400, detail=f"{field_name}: file is not a valid zip/Office archive")


def probe_video_duration_seconds(path: str) -> float:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return float(result.stdout.strip())
    except (subprocess.TimeoutExpired, ValueError, FileNotFoundError):
        return -1.0


def validate_video_duration(path: str, field_name: str) -> float:
    duration = probe_video_duration_seconds(path)
    if duration <= 0:
        os.remove(path)
        raise HTTPException(
            status_code=400,
            detail=f"{field_name}: could not read video duration - file may be corrupt or not a real video"
        )
    if duration < settings.VIDEO_MIN_DURATION_SECONDS or duration > settings.VIDEO_MAX_DURATION_SECONDS:
        os.remove(path)
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field_name}: video duration must be between "
                f"{settings.VIDEO_MIN_DURATION_SECONDS // 60}-{settings.VIDEO_MAX_DURATION_SECONDS // 60} minutes "
                f"(got {duration:.0f}s)"
            )
        )
    return duration
