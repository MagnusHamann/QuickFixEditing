"""Build safe FFmpeg commands from checkbox options."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ffmpeg.filters import (
    audio_distortion_filter,
    blur_filter,
    detailed_line_drawing_filter,
    grayscale_filter,
    line_drawing_filter,
    pixelation_filter,
    resize_filter,
    silhouette_filter,
)
from utils.file_utils import unique_output_path
from utils.validation import validate_trim_times


@dataclass
class ProcessingOptions:
    extract_section: bool = False
    start_time: str = ""
    end_time: str = ""
    extract_audio_only: bool = False
    line_drawing: bool = False
    detailed_line_drawing: bool = False
    pixelation: bool = False
    blur: bool = False
    silhouette: bool = False
    distort_audio: bool = False
    remove_audio: bool = False
    black_white: bool = False
    resize: bool = False
    resize_height: int = 720

    def validate(self) -> None:
        if not self.any_selected:
            raise ValueError("Select at least one operation.")
        if self.extract_section:
            validate_trim_times(self.start_time, self.end_time)
        if self.extract_audio_only and self.remove_audio:
            raise ValueError("Extract audio only cannot be combined with Remove audio.")
        if self.remove_audio and self.distort_audio:
            raise ValueError("Distort audio cannot be combined with Remove audio.")
        if self.extract_audio_only and self.has_video_operation:
            raise ValueError("Extract audio only can only be combined with Extract section.")
        if self.line_drawing and self.detailed_line_drawing:
            raise ValueError("Choose either Cartoon or Detailed cartoon, not both.")

    @property
    def has_video_operation(self) -> bool:
        return any(
            (
                self.line_drawing,
                self.detailed_line_drawing,
                self.pixelation,
                self.blur,
                self.silhouette,
                self.black_white,
                self.resize,
            )
        )

    @property
    def any_selected(self) -> bool:
        return any(
            (
                self.extract_section,
                self.extract_audio_only,
                self.line_drawing,
                self.detailed_line_drawing,
                self.pixelation,
                self.blur,
                self.silhouette,
                self.distort_audio,
                self.remove_audio,
                self.black_white,
                self.resize,
            )
        )


def command_to_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def selected_suffixes(options: ProcessingOptions) -> list[str]:
    suffixes: list[str] = []
    if options.extract_section:
        suffixes.append("trimmed")
    if options.extract_audio_only:
        suffixes.append("audio")
    if options.line_drawing:
        suffixes.append("linedrawing")
    if options.detailed_line_drawing:
        suffixes.append("detailedcartoon")
    if options.pixelation:
        suffixes.append("pixelated")
    if options.blur:
        suffixes.append("blurred")
    if options.silhouette:
        suffixes.append("silhouette")
    if options.distort_audio:
        suffixes.append("audioanon")
    if options.remove_audio:
        suffixes.append("muted")
    if options.black_white:
        suffixes.append("bw")
    if options.resize:
        suffixes.append(f"{options.resize_height}p")
    return suffixes


def video_filters(options: ProcessingOptions) -> list[str]:
    filters: list[str] = []
    if options.line_drawing:
        filters.append(line_drawing_filter())
    if options.detailed_line_drawing:
        filters.append(detailed_line_drawing_filter())
    if options.pixelation:
        filters.append(pixelation_filter())
    if options.blur:
        filters.append(blur_filter())
    if options.silhouette:
        filters.append(silhouette_filter())
    if options.black_white:
        filters.append(grayscale_filter())
    if options.resize:
        filters.append(resize_filter(options.resize_height))
    return filters


def build_command(ffmpeg_path: str, input_file: Path, options: ProcessingOptions) -> tuple[list[str], Path]:
    """Build an FFmpeg command and unique output path."""
    options.validate()
    suffixes = selected_suffixes(options)
    extension = ".mp3" if options.extract_audio_only else ".mp4"
    output_path = unique_output_path(input_file, suffixes, extension)

    command = [
        ffmpeg_path,
        "-hide_banner",
        "-nostdin",
        "-n",
        "-i",
        str(input_file),
    ]

    if options.extract_section:
        command.extend(["-ss", options.start_time, "-to", options.end_time])

    command.extend(["-map_metadata", "-1", "-map_chapters", "-1"])

    if options.extract_audio_only:
        if options.distort_audio:
            command.extend(["-af", audio_distortion_filter()])
        command.extend(["-vn", "-c:a", "libmp3lame", "-q:a", "2", str(output_path)])
        return command, output_path

    filters = video_filters(options)
    command.extend(["-map", "0:v:0"])
    if not options.remove_audio:
        command.extend(["-map", "0:a:0?"])

    if filters or options.extract_section:
        if filters:
            command.extend(["-vf", ",".join(filters)])
        command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"])
    elif options.remove_audio or options.distort_audio:
        command.extend(["-c:v", "copy"])
    else:
        command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"])

    if options.remove_audio:
        command.append("-an")
    else:
        if options.distort_audio:
            command.extend(["-af", audio_distortion_filter()])
        command.extend(["-c:a", "aac", "-b:a", "192k"])

    command.extend(["-movflags", "+faststart", str(output_path)])
    return command, output_path
