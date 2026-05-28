"""File discovery and file metadata helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS
OUTPUT_FOLDER_NAME = "QuickFixEditing files"


@dataclass(frozen=True)
class FileRecord:
    path: Path
    duration_label: str
    resolution_label: str
    size_bytes: int


def is_audio_file(path: Path) -> bool:
    return path.suffix.lower() in AUDIO_EXTENSIONS


def is_video_file(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def collect_media_files(paths: list[Path]) -> list[Path]:
    """Collect supported media files from dropped files and first-level folders."""
    files: list[Path] = []
    for path in paths:
        expanded = path.expanduser()
        if expanded.is_file():
            if expanded.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.append(expanded)
            continue
        if expanded.is_dir():
            folder_files = sorted(
                child for child in expanded.iterdir() if child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS
            )
            files.extend(folder_files)
            continue
        raise ValueError(f"Path not found: {path}")
    return files


def collect_video_files(paths: list[Path]) -> list[Path]:
    """Backward-compatible alias for older call sites."""
    return collect_media_files(paths)


def human_size(size_bytes: int) -> str:
    amount = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{size_bytes} B"


def duration_label(seconds: float | None) -> str:
    if seconds is None:
        return "Unknown"
    total = int(round(seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    secs = total % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def probe_file_record(path: Path, runner) -> FileRecord:
    try:
        info = runner.probe(path)
        duration = duration_label(info.get("duration"))
        width = info.get("width")
        height = info.get("height")
        if width and height:
            resolution = f"{width}x{height}"
        elif info.get("has_audio"):
            resolution = "Audio"
        else:
            resolution = "Unknown"
    except Exception:
        duration = "Unknown"
        resolution = "Audio" if is_audio_file(path) else "Unknown"

    return FileRecord(
        path=path,
        duration_label=duration,
        resolution_label=resolution,
        size_bytes=path.stat().st_size,
    )


def output_directory_for(input_file: Path) -> Path:
    return input_file.parent / OUTPUT_FOLDER_NAME


def unique_output_path(input_file: Path, suffixes: list[str], extension: str) -> Path:
    output_dir = output_directory_for(input_file)
    output_dir.mkdir(parents=True, exist_ok=True)
    suffix = "".join(f"_{suffix}" for suffix in suffixes)
    candidate = output_dir / f"{input_file.stem}{suffix}{extension}"
    if not candidate.exists():
        return candidate

    for index in range(2, 10000):
        numbered = output_dir / f"{input_file.stem}{suffix}_{index}{extension}"
        if not numbered.exists():
            return numbered

    raise FileExistsError(f"Could not create a unique output name for {input_file.name}")
