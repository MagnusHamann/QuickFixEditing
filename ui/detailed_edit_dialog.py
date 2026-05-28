"""Frame preview dialog for tuning anonymisation filters."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from processing.command_builder import DetailedEditSettings, ProcessingOptions, video_filters


class DetailedEditDialog(QDialog):
    """Preview one frame with the same tunable filters used for processing."""

    def __init__(
        self,
        input_file: Path,
        ffmpeg_path: str,
        duration_seconds: float | None,
        options: ProcessingOptions,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Detailed editing")
        self.input_file = input_file
        self.ffmpeg_path = ffmpeg_path
        self.duration_seconds = duration_seconds or 0.0
        self.options = replace(options, detailed_settings=replace(options.detailed_settings))
        self._settings = self.options.detailed_settings
        self._temp_dir = tempfile.TemporaryDirectory(prefix="quickfix_preview_")
        self._cleaned_up = False

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(640, 360)
        self.preview_label.setStyleSheet("background: #0f172a; color: white;")
        self.status_label = QLabel("")
        self.ok_button = QPushButton("Use these settings")
        self.cancel_button = QPushButton("Cancel")
        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(250)

        self._build_layout()
        self._wire_events()
        self._fit_to_screen()
        self._schedule_preview()

    def settings(self) -> DetailedEditSettings:
        return replace(self._settings)

    def done(self, result: int) -> None:
        self._cleanup_temp_dir()
        super().done(result)

    def closeEvent(self, event) -> None:
        self._cleanup_temp_dir()
        super().closeEvent(event)

    def _cleanup_temp_dir(self) -> None:
        if not self._cleaned_up:
            self._temp_dir.cleanup()
            self._cleaned_up = True

    def _build_layout(self) -> None:
        root = QVBoxLayout(self)
        root.addWidget(QLabel(str(self.input_file)))
        root.addWidget(self.preview_label, stretch=1)
        root.addWidget(self.status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        controls = QWidget()
        controls_layout = QVBoxLayout(controls)

        if self.options.line_drawing:
            group = self._slider_group("Cartoon")
            group.layout().addRow("Line detail", self._slider("cartoon_detail", 0, 100, self._settings.cartoon_detail))
            controls_layout.addWidget(group)

        if self.options.detailed_line_drawing:
            group = self._slider_group("Detailed cartoon")
            group.layout().addRow(
                "Line detail",
                self._slider("detailed_cartoon_detail", 0, 100, self._settings.detailed_cartoon_detail),
            )
            group.layout().addRow(
                "Shadows",
                self._slider("detailed_cartoon_shadows", 0, 100, self._settings.detailed_cartoon_shadows),
            )
            controls_layout.addWidget(group)

        if self.options.pixelation:
            group = self._slider_group("Pixelation")
            group.layout().addRow("Pixel size", self._slider("pixel_size", 4, 50, self._settings.pixel_size))
            controls_layout.addWidget(group)

        if self.options.blur:
            group = self._slider_group("Blur")
            group.layout().addRow("Blur strength", self._slider("blur_sigma", 1, 60, self._settings.blur_sigma))
            controls_layout.addWidget(group)

        if self.options.silhouette:
            group = self._slider_group("Silhouette")
            group.layout().addRow(
                "Privacy strength",
                self._slider("silhouette_strength", 0, 100, self._settings.silhouette_strength),
            )
            controls_layout.addWidget(group)

        if self.options.black_white:
            group = self._slider_group("Black and white")
            group.layout().addRow(
                "Contrast",
                self._slider("grayscale_contrast", 50, 180, self._settings.grayscale_contrast),
            )
            controls_layout.addWidget(group)

        if controls_layout.count() == 0:
            controls_layout.addWidget(QLabel("No video anonymisation options selected."))

        controls_layout.addStretch(1)
        scroll.setWidget(controls)
        root.addWidget(scroll)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.ok_button)
        buttons.addWidget(self.cancel_button)
        root.addLayout(buttons)

    def _fit_to_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(980, 720)
            return
        available = screen.availableGeometry()
        width = min(980, max(720, available.width() - 100))
        height = min(720, max(520, available.height() - 100))
        self.resize(width, height)

    def _wire_events(self) -> None:
        self._preview_timer.timeout.connect(self._render_preview)
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _slider_group(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        group.setLayout(QFormLayout())
        return group

    def _slider(self, field_name: str, minimum: int, maximum: int, value: int) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        value_label = QLabel(str(value))
        value_label.setMinimumWidth(36)

        def update_setting(new_value: int) -> None:
            setattr(self._settings, field_name, new_value)
            value_label.setText(str(new_value))
            self._schedule_preview()

        slider.valueChanged.connect(update_setting)
        layout.addWidget(slider)
        layout.addWidget(value_label)
        return container

    def _schedule_preview(self) -> None:
        self.status_label.setText("Rendering preview...")
        self._preview_timer.start()

    def _render_preview(self) -> None:
        output_path = Path(self._temp_dir.name) / "preview.png"
        timestamp = max(0.0, self.duration_seconds / 2)
        preview_options = replace(self.options, detailed_settings=self._settings)
        filters = video_filters(preview_options)
        command = [
            self.ffmpeg_path,
            "-hide_banner",
            "-y",
            "-ss",
            f"{timestamp:.3f}",
            "-i",
            str(self.input_file),
            "-frames:v",
            "1",
        ]
        if filters:
            command.extend(["-vf", ",".join(filters)])
        command.append(str(output_path))

        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if completed.returncode != 0 or not output_path.exists():
            detail = completed.stderr.strip() or completed.stdout.strip() or "Could not render preview."
            self.status_label.setText(detail.splitlines()[-1][:220])
            return

        pixmap = QPixmap(str(output_path))
        if pixmap.isNull():
            self.status_label.setText("Could not load preview frame.")
            return

        scaled = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview_label.setPixmap(scaled)
        self.status_label.setText("")

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.preview_label.pixmap():
            self._schedule_preview()
