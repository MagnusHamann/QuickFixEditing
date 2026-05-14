"""Input validation helpers."""

from __future__ import annotations

import re


TIME_PATTERN = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")


def parse_time_to_seconds(value: str, label: str) -> int:
    """Parse mm:ss or hh:mm:ss into seconds."""
    clean = value.strip()
    if not TIME_PATTERN.fullmatch(clean):
        raise ValueError(f"{label} must use mm:ss or hh:mm:ss.")

    parts = [int(part) for part in clean.split(":")]
    if len(parts) == 2:
        minutes, seconds = parts
        hours = 0
    else:
        hours, minutes, seconds = parts

    if minutes > 59 or seconds > 59:
        raise ValueError(f"{label} has minutes or seconds outside the valid range.")

    return hours * 3600 + minutes * 60 + seconds


def validate_trim_times(start: str, end: str) -> None:
    start_seconds = parse_time_to_seconds(start, "Start time")
    end_seconds = parse_time_to_seconds(end, "End time")
    if end_seconds <= start_seconds:
        raise ValueError("End time must be greater than start time.")
