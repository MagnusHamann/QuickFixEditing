"""Waveform-based editor for marking audio ranges to silence."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import wave
from array import array
from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPaintEvent, QPainter, QPen
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from processing.command_builder import normalized_ranges


def format_seconds(seconds: float) -> str:
    """Return a compact timestamp for human-facing range labels."""
    seconds = max(0.0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    remaining = seconds % 60
    if hours:
        return f"{hours:02d}:{minutes:02d}:{remaining:04.1f}"
    return f"{minutes:02d}:{remaining:04.1f}"


def read_waveform_summary(wav_path: Path) -> tuple[float, list[tuple[float, float]]]:
    """Read a mono 16-bit WAV and return duration plus min/max peaks."""
    with wave.open(str(wav_path), "rb") as handle:
        sample_rate = handle.getframerate()
        total_frames = handle.getnframes()
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()

        if channels != 1 or sample_width != 2:
            raise RuntimeError("Temporary waveform audio was not mono 16-bit PCM.")

        duration = total_frames / sample_rate if sample_rate else 0.0
        bucket_count = max(600, min(6000, int(max(duration, 1.0) * 25)))
        mins = [1.0] * bucket_count
        maxes = [-1.0] * bucket_count

        frame_index = 0
        while frame_index < total_frames:
            data = handle.readframes(8192)
            if not data:
                break
            samples = array("h")
            samples.frombytes(data)
            if sys.byteorder != "little":
                samples.byteswap()

            for sample in samples:
                bucket = min(bucket_count - 1, int(frame_index * bucket_count / max(total_frames, 1)))
                value = max(-1.0, min(1.0, sample / 32768.0))
                mins[bucket] = min(mins[bucket], value)
                maxes[bucket] = max(maxes[bucket], value)
                frame_index += 1

    peaks = []
    for minimum, maximum in zip(mins, maxes):
        if minimum == 1.0 and maximum == -1.0:
            peaks.append((0.0, 0.0))
        else:
            peaks.append((minimum, maximum))
    return duration, peaks


class WaveformView(QWidget):
    """Simple waveform canvas with drag-to-select range support."""

    selection_changed = Signal(float, float)

    def __init__(self, duration: float, peaks: list[tuple[float, float]], ranges: Sequence[tuple[float, float]]) -> None:
        super().__init__()
        self.duration = max(0.0, duration)
        self.peaks = peaks
        self.ranges = normalized_ranges(ranges)
        self.playhead_seconds: float | None = None
        self._drag_start: float | None = None
        self._drag_current: float | None = None
        self.setMinimumHeight(230)
        self.setMouseTracking(True)

    def set_ranges(self, ranges: Sequence[tuple[float, float]]) -> None:
        self.ranges = normalized_ranges(ranges)
        self.update()

    def set_playhead(self, seconds: float | None) -> None:
        self.playhead_seconds = None if seconds is None else max(0.0, min(self.duration, seconds))
        self.update()

    def selected_range(self) -> tuple[float, float] | None:
        if self._drag_start is None or self._drag_current is None:
            return None
        start, end = sorted((self._drag_start, self._drag_current))
        if end - start < 0.05:
            return None
        return start, end

    def clear_selection(self) -> None:
        self._drag_start = None
        self._drag_current = None
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        canvas = self.rect().adjusted(10, 10, -10, -26)
        painter.fillRect(self.rect(), QColor("#f6f8fb"))
        painter.fillRect(canvas, QColor("#ffffff"))
        painter.setPen(QPen(QColor("#d6dde8"), 1))
        painter.drawRect(canvas)

        for start, end in self.ranges:
            self._paint_range(painter, canvas, start, end, QColor(255, 181, 82, 80))

        selected = self.selected_range()
        if selected:
            self._paint_range(painter, canvas, selected[0], selected[1], QColor(68, 132, 255, 90))

        if self.peaks:
            center = canvas.center().y()
            half_height = max(1, canvas.height() // 2 - 8)
            painter.setPen(QPen(QColor("#243043"), 1))
            count = len(self.peaks)
            for index, (minimum, maximum) in enumerate(self.peaks):
                x = canvas.left() + int(index * canvas.width() / max(count - 1, 1))
                y_top = center - int(maximum * half_height)
                y_bottom = center - int(minimum * half_height)
                painter.drawLine(x, y_top, x, y_bottom)

        if self.playhead_seconds is not None:
            x = self._x_for_seconds(self.playhead_seconds, canvas.left(), canvas.width())
            painter.setPen(QPen(QColor("#dc2626"), 2))
            painter.drawLine(x, canvas.top(), x, canvas.bottom())

        painter.setPen(QPen(QColor("#5f6c7b"), 1))
        painter.drawText(canvas.left(), self.rect().bottom() - 7, "00:00.0")
        painter.drawText(canvas.right() - 70, self.rect().bottom() - 7, format_seconds(self.duration))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton or self.duration <= 0:
            return
        self._drag_start = self._seconds_at_x(event.position().x())
        self._drag_current = self._drag_start
        self.selection_changed.emit(self._drag_start, self._drag_current)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start is None or self.duration <= 0:
            return
        self._drag_current = self._seconds_at_x(event.position().x())
        start, end = sorted((self._drag_start, self._drag_current))
        self.selection_changed.emit(start, end)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.LeftButton or self._drag_start is None:
            return
        self._drag_current = self._seconds_at_x(event.position().x())
        start, end = sorted((self._drag_start, self._drag_current))
        self.selection_changed.emit(start, end)
        self.update()

    def _seconds_at_x(self, x_position: float) -> float:
        canvas = self.rect().adjusted(10, 10, -10, -26)
        if canvas.width() <= 0:
            return 0.0
        ratio = (x_position - canvas.left()) / canvas.width()
        return max(0.0, min(self.duration, ratio * self.duration))

    def _x_for_seconds(self, seconds: float, left: int, width: int) -> int:
        if self.duration <= 0:
            return left
        return left + int((seconds / self.duration) * width)

    def _paint_range(self, painter: QPainter, canvas, start: float, end: float, color: QColor) -> None:
        left = self._x_for_seconds(start, canvas.left(), canvas.width())
        right = self._x_for_seconds(end, canvas.left(), canvas.width())
        painter.fillRect(left, canvas.top(), max(1, right - left), canvas.height(), color)


class WaveformEditorDialog(QDialog):
    """Dialog that generates a temporary WAV and lets users mark silence ranges."""

    def __init__(
        self,
        input_file: Path,
        ffmpeg_path: str,
        existing_ranges: Sequence[tuple[float, float]] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Silence selected waveform")
        self.input_file = input_file
        self.ffmpeg_path = ffmpeg_path
        self._temp_dir = tempfile.TemporaryDirectory(prefix="quickfix_waveform_")
        self._cleaned_up = False
        self._ranges = normalized_ranges(existing_ranges or [])
        self._play_until_ms: int | None = None

        self.wav_path = self._create_temp_wav()
        duration, peaks = read_waveform_summary(self.wav_path)

        self.file_label = QLabel(str(input_file))
        self.view = WaveformView(duration, peaks, self._ranges)
        self.play_all_button = QPushButton("Play all")
        self.play_selection_button = QPushButton("Play selection")
        self.pause_button = QPushButton("Pause / resume")
        self.stop_button = QPushButton("Stop")
        self.position_label = QLabel(f"00:00.0 / {format_seconds(duration)}")
        self.selection_label = QLabel("Drag across the waveform to select a section.")
        self.range_list = QListWidget()
        self.add_button = QPushButton("Add silence section")
        self.remove_button = QPushButton("Remove selected")
        self.clear_button = QPushButton("Clear all")
        self.ok_button = QPushButton("Use these sections")
        self.cancel_button = QPushButton("Cancel")
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(str(self.wav_path)))
        self.audio_output.setVolume(1.0)

        self._build_layout()
        self._wire_events()
        self._fit_to_screen()
        self._refresh_ranges()

    def ranges(self) -> list[tuple[float, float]]:
        return list(self._ranges)

    def closeEvent(self, event) -> None:
        self._cleanup_temp_dir()
        super().closeEvent(event)

    def done(self, result: int) -> None:
        self._cleanup_temp_dir()
        super().done(result)

    def _cleanup_temp_dir(self) -> None:
        if not self._cleaned_up:
            self._stop_playback(clear_playhead=True)
            self._temp_dir.cleanup()
            self._cleaned_up = True

    def _build_layout(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(self.file_label)
        root.addWidget(self.view, stretch=1)
        playback_buttons = QHBoxLayout()
        playback_buttons.addWidget(self.play_all_button)
        playback_buttons.addWidget(self.play_selection_button)
        playback_buttons.addWidget(self.pause_button)
        playback_buttons.addWidget(self.stop_button)
        playback_buttons.addStretch(1)
        playback_buttons.addWidget(self.position_label)
        root.addLayout(playback_buttons)
        root.addWidget(self.selection_label)
        root.addWidget(QLabel("Sections to silence"))
        root.addWidget(self.range_list)

        range_buttons = QHBoxLayout()
        range_buttons.addWidget(self.add_button)
        range_buttons.addWidget(self.remove_button)
        range_buttons.addWidget(self.clear_button)
        range_buttons.addStretch(1)
        root.addLayout(range_buttons)

        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch(1)
        dialog_buttons.addWidget(self.ok_button)
        dialog_buttons.addWidget(self.cancel_button)
        root.addLayout(dialog_buttons)

    def _fit_to_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(860, 520)
            return
        available = screen.availableGeometry()
        width = min(860, max(680, available.width() - 100))
        height = min(560, max(460, available.height() - 100))
        self.resize(width, height)

    def _wire_events(self) -> None:
        self.view.selection_changed.connect(self._update_selection_label)
        self.play_all_button.clicked.connect(self._play_all)
        self.play_selection_button.clicked.connect(self._play_selection)
        self.pause_button.clicked.connect(self._toggle_pause)
        self.stop_button.clicked.connect(lambda: self._stop_playback(clear_playhead=True))
        self.player.positionChanged.connect(self._player_position_changed)
        self.add_button.clicked.connect(self._add_selected_range)
        self.remove_button.clicked.connect(self._remove_selected_range)
        self.clear_button.clicked.connect(self._clear_ranges)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _create_temp_wav(self) -> Path:
        wav_path = Path(self._temp_dir.name) / "waveform.wav"
        command = [
            self.ffmpeg_path,
            "-hide_banner",
            "-y",
            "-i",
            str(self.input_file),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "8000",
            "-acodec",
            "pcm_s16le",
            str(wav_path),
        ]
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip() or "FFmpeg could not create a waveform preview."
            raise RuntimeError(detail)
        return wav_path

    def _update_selection_label(self, start: float, end: float) -> None:
        if end - start < 0.05:
            self.selection_label.setText("Drag across the waveform to select a section.")
            return
        self.selection_label.setText(f"Selected: {format_seconds(start)} to {format_seconds(end)}")

    def _play_all(self) -> None:
        self._start_playback(0.0, self.view.duration)

    def _play_selection(self) -> None:
        selected = self.view.selected_range()
        if selected is None:
            row = self.range_list.currentRow()
            if row >= 0:
                selected = self._ranges[row]
        if selected is None:
            self.selection_label.setText("Select a waveform section, or choose a saved section, before playing it.")
            return
        self._start_playback(selected[0], selected[1])

    def _start_playback(self, start: float, end: float) -> None:
        start_ms = int(max(0.0, start) * 1000)
        end_ms = int(max(start, end) * 1000)
        self._play_until_ms = end_ms
        self.player.setPosition(start_ms)
        self.player.play()

    def _toggle_pause(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def _stop_playback(self, clear_playhead: bool = False) -> None:
        self._play_until_ms = None
        self.player.stop()
        if clear_playhead:
            self.view.set_playhead(None)
            self.position_label.setText(f"00:00.0 / {format_seconds(self.view.duration)}")

    def _player_position_changed(self, position_ms: int) -> None:
        seconds = position_ms / 1000
        if self._play_until_ms is not None and position_ms >= self._play_until_ms:
            seconds = self._play_until_ms / 1000
            self._play_until_ms = None
            self.player.pause()
        self.view.set_playhead(seconds)
        self.position_label.setText(f"{format_seconds(seconds)} / {format_seconds(self.view.duration)}")

    def _add_selected_range(self) -> None:
        selected = self.view.selected_range()
        if not selected:
            self.selection_label.setText("Select a longer section before adding it.")
            return
        self._ranges = normalized_ranges([*self._ranges, selected])
        self.view.clear_selection()
        self._refresh_ranges()

    def _remove_selected_range(self) -> None:
        row = self.range_list.currentRow()
        if row < 0:
            return
        self._ranges.pop(row)
        self._refresh_ranges()

    def _clear_ranges(self) -> None:
        self._ranges = []
        self._refresh_ranges()

    def _refresh_ranges(self) -> None:
        self.range_list.clear()
        for start, end in self._ranges:
            self.range_list.addItem(f"{format_seconds(start)} to {format_seconds(end)}")
        self.view.set_ranges(self._ranges)
