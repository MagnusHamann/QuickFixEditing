"""Build safe FFmpeg commands from checkbox options."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

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
from utils.file_utils import is_audio_file, unique_output_path
from utils.validation import validate_trim_times


@dataclass
class DetailedEditSettings:
    cartoon_detail: int = 50
    detailed_cartoon_detail: int = 55
    detailed_cartoon_shadows: int = 60
    pixel_size: int = 20
    blur_sigma: int = 20
    silhouette_strength: int = 50
    grayscale_contrast: int = 100


@dataclass
class ProcessingOptions:
    extract_section: bool = False
    start_time: str = ""
    end_time: str = ""
    extract_audio_only: bool = False
    silence_section: bool = False
    silence_start_time: str = ""
    silence_end_time: str = ""
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
    detailed_settings: DetailedEditSettings = field(default_factory=DetailedEditSettings)

    def validate(self, has_file_silence_ranges: bool = False) -> None:
        if not self.any_selected:
            raise ValueError("Select at least one operation.")
        if self.extract_section:
            validate_trim_times(self.start_time, self.end_time)
        if self.silence_section:
            if self.has_silence_times:
                validate_trim_times(self.silence_start_time, self.silence_end_time)
            elif self.has_any_silence_time:
                raise ValueError("Silence section needs both a start time and an end time.")
            elif not has_file_silence_ranges:
                raise ValueError("Enter silence start/end times or add silence ranges with the waveform editor.")
        if self.extract_audio_only and self.remove_audio:
            raise ValueError("Extract audio only cannot be combined with Remove audio.")
        if self.remove_audio and self.distort_audio:
            raise ValueError("Distort audio cannot be combined with Remove audio.")
        if self.remove_audio and self.silence_section:
            raise ValueError("Silence section cannot be combined with Remove audio.")
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
                self.silence_section,
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

    @property
    def any_selected_excluding_silence(self) -> bool:
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

    @property
    def has_silence_times(self) -> bool:
        return bool(self.silence_start_time.strip() and self.silence_end_time.strip())

    @property
    def has_any_silence_time(self) -> bool:
        return bool(self.silence_start_time.strip() or self.silence_end_time.strip())


def command_to_text(command: list[str]) -> str:
    return subprocess.list2cmdline(command)


def selected_suffixes(options: ProcessingOptions) -> list[str]:
    suffixes: list[str] = []
    if options.extract_section:
        suffixes.append("trimmed")
    if options.extract_audio_only:
        suffixes.append("audio")
    if options.silence_section:
        suffixes.append("silenced")
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
    settings = options.detailed_settings
    if options.line_drawing:
        filters.append(line_drawing_filter(settings.cartoon_detail))
    if options.detailed_line_drawing:
        filters.append(detailed_line_drawing_filter(settings.detailed_cartoon_detail, settings.detailed_cartoon_shadows))
    if options.pixelation:
        filters.append(pixelation_filter(settings.pixel_size))
    if options.blur:
        filters.append(blur_filter(settings.blur_sigma))
    if options.silhouette:
        filters.append(silhouette_filter(settings.silhouette_strength))
    if options.black_white:
        filters.append(grayscale_filter(settings.grayscale_contrast))
    if options.resize:
        filters.append(resize_filter(options.resize_height))
    return filters


def normalized_ranges(ranges: Sequence[tuple[float, float]]) -> list[tuple[float, float]]:
    """Return sorted, merged ranges with invalid zero-length entries removed."""
    clean = sorted((float(start), float(end)) for start, end in ranges if float(end) > float(start))
    if not clean:
        return []

    merged: list[tuple[float, float]] = [clean[0]]
    for start, end in clean[1:]:
        previous_start, previous_end = merged[-1]
        if start <= previous_end:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return merged


def silence_ranges(options: ProcessingOptions, file_silence_ranges: Sequence[tuple[float, float]] | None = None) -> list[tuple[float, float]]:
    ranges: list[tuple[float, float]] = []
    if options.silence_section and options.has_silence_times:
        from utils.validation import parse_time_to_seconds

        ranges.append(
            (
                float(parse_time_to_seconds(options.silence_start_time, "Silence start time")),
                float(parse_time_to_seconds(options.silence_end_time, "Silence end time")),
            )
        )
    if options.silence_section and file_silence_ranges:
        ranges.extend(file_silence_ranges)
    return normalized_ranges(ranges)


def silence_filter(ranges: Sequence[tuple[float, float]]) -> str:
    filters = []
    for start, end in normalized_ranges(ranges):
        filters.append(f"volume=volume=0:enable='between(t,{start:.3f},{end:.3f})'")
    return ",".join(filters)


def audio_filters(options: ProcessingOptions, ranges: Sequence[tuple[float, float]]) -> list[str]:
    filters: list[str] = []
    if options.distort_audio:
        filters.append(audio_distortion_filter())
    if options.silence_section and ranges:
        filters.append(silence_filter(ranges))
    return filters


def build_command(
    ffmpeg_path: str,
    input_file: Path,
    options: ProcessingOptions,
    file_silence_ranges: Sequence[tuple[float, float]] | None = None,
) -> tuple[list[str], Path]:
    """Build an FFmpeg command and unique output path."""
    input_is_audio = is_audio_file(input_file)
    ranges = silence_ranges(options, file_silence_ranges)
    options.validate(has_file_silence_ranges=bool(ranges))
    if input_is_audio:
        validate_audio_input_options(options)
    suffixes = selected_suffixes(options)
    extension = ".mp3" if (input_is_audio or options.extract_audio_only) else ".mp4"
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

    if input_is_audio:
        return build_audio_command(command, output_path, options, ranges)

    if options.extract_audio_only:
        audio_filter_chain = audio_filters(options, ranges)
        if audio_filter_chain:
            command.extend(["-af", ",".join(audio_filter_chain)])
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
    elif options.remove_audio or options.distort_audio or options.silence_section:
        command.extend(["-c:v", "copy"])
    else:
        command.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p"])

    if options.remove_audio:
        command.append("-an")
    else:
        audio_filter_chain = audio_filters(options, ranges)
        if audio_filter_chain:
            command.extend(["-af", ",".join(audio_filter_chain)])
        command.extend(["-c:a", "aac", "-b:a", "192k"])

    command.extend(["-movflags", "+faststart", str(output_path)])
    return command, output_path


def validate_audio_input_options(options: ProcessingOptions) -> None:
    if options.has_video_operation:
        raise ValueError("Video anonymisation, black-and-white, and resize options can only be used with video files.")
    if options.remove_audio:
        raise ValueError("Remove audio cannot be used on audio-only files.")


def build_audio_command(
    command: list[str],
    output_path: Path,
    options: ProcessingOptions,
    ranges: Sequence[tuple[float, float]],
) -> tuple[list[str], Path]:
    audio_filter_chain = audio_filters(options, ranges)
    command.extend(["-vn", "-map", "0:a:0"])
    if audio_filter_chain:
        command.extend(["-af", ",".join(audio_filter_chain)])
    command.extend(["-c:a", "libmp3lame", "-q:a", "2", str(output_path)])
    return command, output_path
