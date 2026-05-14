"""Checkbox options panel."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from processing.command_builder import ProcessingOptions


class OptionsPanel(QWidget):
    """Collects user-selected FFmpeg operations."""

    options_changed = Signal()

    def __init__(self) -> None:
        super().__init__()

        self.extract_section = QCheckBox("Extract section")
        self.start_time = QLineEdit()
        self.end_time = QLineEdit()
        self.start_time.setPlaceholderText("mm:ss or hh:mm:ss")
        self.end_time.setPlaceholderText("mm:ss or hh:mm:ss")

        self.extract_audio = QCheckBox("Extract audio only")
        self.line_drawing = QCheckBox("Light anonymisation (cartoon line drawing)")
        self.pixelation = QCheckBox("Medium anonymisation (pixelation)")
        self.blur = QCheckBox("Strong anonymisation (blur)")
        self.silhouette = QCheckBox("Extreme anonymisation (silhouette mode)")
        self.distort_audio = QCheckBox("Distort audio (TV-style voice anonymisation)")
        self.remove_audio = QCheckBox("Remove audio")
        self.black_white = QCheckBox("Black and white")
        self.resize = QCheckBox("Resize video")

        self.resize_height = QComboBox()
        self.resize_height.addItems(["480p", "720p", "1080p"])
        self.resize_height.setEnabled(False)

        self.preset_observation = QPushButton("Observation sharing")
        self.preset_interview = QPushButton("Interview review")
        self.preset_fieldnote = QPushButton("Fieldnote coding")
        self.preset_maximum = QPushButton("Maximum participant privacy")
        self.preset_audio = QPushButton("Audio for transcription")

        self._build_layout()
        self._wire_events()
        self._update_visibility()

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        group = QGroupBox("Operations")
        group_layout = QVBoxLayout(group)

        for checkbox in (
            self.extract_section,
            self.extract_audio,
            self.line_drawing,
            self.pixelation,
            self.blur,
            self.silhouette,
            self.distort_audio,
            self.remove_audio,
            self.black_white,
            self.resize,
        ):
            group_layout.addWidget(checkbox)

        self.trim_group = QGroupBox("Section times")
        trim_layout = QFormLayout(self.trim_group)
        trim_layout.addRow("Start", self.start_time)
        trim_layout.addRow("End", self.end_time)
        group_layout.addWidget(self.trim_group)

        resize_row = QFormLayout()
        resize_row.addRow(QLabel("Size"), self.resize_height)
        group_layout.addLayout(resize_row)

        presets = QGroupBox("Presets")
        preset_layout = QVBoxLayout(presets)
        for button in (
            self.preset_observation,
            self.preset_interview,
            self.preset_fieldnote,
            self.preset_maximum,
            self.preset_audio,
        ):
            button.setCursor(Qt.PointingHandCursor)
            preset_layout.addWidget(button)

        layout.addWidget(group)
        layout.addWidget(presets)
        layout.addStretch(1)

    def _wire_events(self) -> None:
        for checkbox in self.findChildren(QCheckBox):
            checkbox.toggled.connect(self._update_visibility)
            checkbox.toggled.connect(self.options_changed)
        self.start_time.textChanged.connect(self.options_changed)
        self.end_time.textChanged.connect(self.options_changed)
        self.resize_height.currentTextChanged.connect(self.options_changed)

        self.preset_observation.clicked.connect(self.apply_observation_preset)
        self.preset_interview.clicked.connect(self.apply_interview_preset)
        self.preset_fieldnote.clicked.connect(self.apply_fieldnote_preset)
        self.preset_maximum.clicked.connect(self.apply_maximum_preset)
        self.preset_audio.clicked.connect(self.apply_audio_preset)

    def _update_visibility(self) -> None:
        self.trim_group.setVisible(self.extract_section.isChecked())
        self.resize_height.setEnabled(self.resize.isChecked())

    def clear_all(self) -> None:
        for checkbox in self.findChildren(QCheckBox):
            checkbox.setChecked(False)

    def apply_observation_preset(self) -> None:
        self.clear_all()
        self.line_drawing.setChecked(True)
        self.remove_audio.setChecked(True)

    def apply_interview_preset(self) -> None:
        self.clear_all()
        self.pixelation.setChecked(True)
        self.distort_audio.setChecked(True)

    def apply_fieldnote_preset(self) -> None:
        self.clear_all()
        self.line_drawing.setChecked(True)
        self.black_white.setChecked(True)
        self.resize.setChecked(True)
        self.resize_height.setCurrentText("720p")

    def apply_maximum_preset(self) -> None:
        self.clear_all()
        self.silhouette.setChecked(True)
        self.distort_audio.setChecked(True)

    def apply_audio_preset(self) -> None:
        self.clear_all()
        self.extract_audio.setChecked(True)

    def selected_options(self) -> ProcessingOptions:
        resize_label = self.resize_height.currentText()
        return ProcessingOptions(
            extract_section=self.extract_section.isChecked(),
            start_time=self.start_time.text().strip(),
            end_time=self.end_time.text().strip(),
            extract_audio_only=self.extract_audio.isChecked(),
            line_drawing=self.line_drawing.isChecked(),
            pixelation=self.pixelation.isChecked(),
            blur=self.blur.isChecked(),
            silhouette=self.silhouette.isChecked(),
            distort_audio=self.distort_audio.isChecked(),
            remove_audio=self.remove_audio.isChecked(),
            black_white=self.black_white.isChecked(),
            resize=self.resize.isChecked(),
            resize_height=int(resize_label.replace("p", "")),
        )
