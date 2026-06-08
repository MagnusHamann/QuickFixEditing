"""Main application window."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Slot
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ffmpeg.ffmpeg_runner import FFmpegRunner, find_ffmpeg_tools
from processing.batch_processor import BatchProcessor
from ui.drag_drop_widget import DragDropWidget
from ui.detailed_edit_dialog import DetailedEditDialog
from ui.options_panel import OptionsPanel
from ui.waveform_editor import WaveformEditorDialog, format_seconds
from utils.file_utils import FileRecord, collect_media_files, human_size, is_audio_file, is_video_file, probe_file_record
from utils.validation import parse_time_to_seconds


class MainWindow(QMainWindow):
    """Top-level UI: drop area, file list, options, and processing log."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("QuickFix Editing")
        self.records: list[FileRecord] = []
        self.silence_ranges_by_path: dict[Path, list[tuple[float, float]]] = {}
        self.worker_thread: QThread | None = None
        self.worker: BatchProcessor | None = None
        self.runner = FFmpegRunner()

        self.drop_zone = DragDropWidget()
        self.table = QTableWidget(0, 5)
        self.options_panel = OptionsPanel()
        self.start_button = QPushButton("Start Processing")
        self.cancel_button = QPushButton("Cancel")
        self.progress = QProgressBar()
        self.log = QPlainTextEdit()
        self.status = QStatusBar()

        self._build_ui()
        self._wire_events()
        self._check_ffmpeg()
        self._fit_to_screen()

    def _build_ui(self) -> None:
        add_files = QAction("Add files", self)
        add_folder = QAction("Add folder", self)
        detailed_edit = QAction("Detailed editing", self)
        edit_silence = QAction("Edit silence waveform", self)
        clear = QAction("Clear list", self)
        self.toolbar = self.addToolBar("Files")
        self.toolbar.addAction(add_files)
        self.toolbar.addAction(add_folder)
        self.toolbar.addAction(detailed_edit)
        self.toolbar.addAction(edit_silence)
        self.toolbar.addAction(clear)
        add_files.triggered.connect(self.choose_files)
        add_folder.triggered.connect(self.choose_folder)
        detailed_edit.triggered.connect(self.open_detailed_editing)
        edit_silence.triggered.connect(self.edit_selected_silence)
        clear.triggered.connect(self.clear_files)

        self.table.setHorizontalHeaderLabels(["Filename", "Duration", "Details", "Size", "Silence"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(self.drop_zone)
        left_layout.addWidget(QLabel("Detected files"))
        left_layout.addWidget(self.table, stretch=1)

        options_scroll = QScrollArea()
        options_scroll.setWidgetResizable(True)
        options_scroll.setWidget(self.options_panel)
        options_scroll.setMinimumWidth(300)
        options_scroll.setMaximumWidth(420)
        options_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(options_scroll)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)

        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(2000)
        self.log.setMaximumHeight(190)
        self.cancel_button.setEnabled(False)
        self.progress.setRange(0, 100)

        bottom_buttons = QHBoxLayout()
        bottom_buttons.addWidget(self.start_button)
        bottom_buttons.addWidget(self.cancel_button)
        bottom_buttons.addWidget(self.progress)
        left_layout.addLayout(bottom_buttons)
        left_layout.addWidget(QLabel("Processing log"))
        left_layout.addWidget(self.log, stretch=0)

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addWidget(splitter, stretch=1)

        self.setCentralWidget(root)
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

        self.setStyleSheet(
            """
            QPushButton {
                min-height: 30px;
                padding: 6px 12px;
            }
            QPushButton#Primary {
                font-weight: 600;
            }
            QPlainTextEdit {
                background: #101827;
                color: #d7e1f0;
                font-family: Consolas, Menlo, monospace;
            }
            """
        )
        self.start_button.setObjectName("Primary")

    def _fit_to_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if not screen:
            self.resize(1180, 760)
            return

        available = screen.availableGeometry()
        width = min(1180, max(760, available.width() - 80))
        height = min(820, max(560, available.height() - 80))
        self.resize(width, height)
        self.setMinimumSize(min(760, width), min(520, height))

    def _wire_events(self) -> None:
        self.drop_zone.paths_dropped.connect(self.add_paths)
        self.start_button.clicked.connect(self.start_processing)
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.options_panel.edit_silence_requested.connect(self.edit_selected_silence)
        self.options_panel.detailed_edit_requested.connect(self.open_detailed_editing)

    def _check_ffmpeg(self) -> None:
        ffmpeg, ffprobe = find_ffmpeg_tools()
        if not ffmpeg or not ffprobe:
            QMessageBox.warning(
                self,
                "FFmpeg not found",
                "FFmpeg and FFprobe were not found. Install FFmpeg and restart the application.",
            )
            self.status.showMessage("FFmpeg not found")
            return
        self.runner.ffmpeg_path = ffmpeg
        self.runner.ffprobe_path = ffprobe
        self.status.showMessage(f"Using FFmpeg: {ffmpeg}")

    @Slot()
    def choose_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Choose media files",
            "",
            "Media files (*.mp4 *.mov *.mkv *.avi *.mp3 *.wav *.m4a *.flac *.aac *.ogg)",
        )
        if paths:
            self.add_paths(paths)

    @Slot()
    def choose_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose a folder")
        if folder:
            self.add_paths([folder])

    @Slot(list)
    def add_paths(self, raw_paths: list[str]) -> None:
        try:
            files = collect_media_files([Path(path) for path in raw_paths])
        except ValueError as exc:
            QMessageBox.warning(self, "Input problem", str(exc))
            return

        if not files:
            QMessageBox.information(self, "No media found", "No supported video or audio files were found.")
            return

        existing = {record.path.resolve() for record in self.records}
        added = 0
        for file_path in files:
            resolved = file_path.resolve()
            if resolved in existing:
                continue
            record = probe_file_record(resolved, self.runner)
            self.records.append(record)
            existing.add(resolved)
            added += 1

        self.refresh_table()
        self.status.showMessage(f"Added {added} file(s). {len(self.records)} total.")

    def refresh_table(self) -> None:
        self.table.setRowCount(len(self.records))
        for row, record in enumerate(self.records):
            values = [
                record.path.name,
                record.duration_label,
                record.resolution_label,
                human_size(record.size_bytes),
                self._silence_label(record.path),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setToolTip(str(record.path))
                self.table.setItem(row, column, item)

    @Slot()
    def clear_files(self) -> None:
        self.records.clear()
        self.silence_ranges_by_path.clear()
        self.refresh_table()
        self.status.showMessage("File list cleared")

    @Slot()
    def edit_selected_silence(self) -> None:
        if not self.runner.ready or not self.runner.ffmpeg_path:
            QMessageBox.warning(self, "FFmpeg not found", "Install FFmpeg before creating waveform previews.")
            return

        record = self.selected_record()
        if not record:
            return

        existing = self.silence_ranges_by_path.get(record.path.resolve(), [])
        try:
            dialog = WaveformEditorDialog(record.path, self.runner.ffmpeg_path, existing, self)
        except Exception as exc:
            QMessageBox.warning(self, "Waveform problem", str(exc))
            return

        if dialog.exec() != QDialog.Accepted:
            return

        ranges = dialog.ranges()
        resolved = record.path.resolve()
        if ranges:
            self.silence_ranges_by_path[resolved] = ranges
            self.options_panel.enable_silence_section()
            self.status.showMessage(f"Saved {len(ranges)} silence range(s) for {record.path.name}.")
        else:
            self.silence_ranges_by_path.pop(resolved, None)
            self.status.showMessage(f"Cleared silence ranges for {record.path.name}.")
        self.refresh_table()

    @Slot()
    def open_detailed_editing(self) -> None:
        if not self.runner.ready or not self.runner.ffmpeg_path:
            QMessageBox.warning(self, "FFmpeg not found", "Install FFmpeg before creating preview frames.")
            return

        record = self.selected_video_record()
        if not record:
            return

        options = self.options_panel.selected_options()
        if not options.has_video_operation:
            QMessageBox.information(self, "No video options", "Select at least one video editing option first.")
            return

        try:
            duration = self.runner.probe(record.path).get("duration")
            dialog = DetailedEditDialog(record.path, self.runner.ffmpeg_path, duration, options, self)
        except Exception as exc:
            QMessageBox.warning(self, "Preview problem", str(exc))
            return

        if dialog.exec() != QDialog.Accepted:
            return

        self.options_panel.detailed_settings = dialog.settings()
        self.status.showMessage(f"Detailed editing settings saved for the current operation choices.")

    @Slot()
    def start_processing(self) -> None:
        if not self.records:
            QMessageBox.information(self, "No files", "Drop or choose at least one media file first.")
            return
        if not self.runner.ready:
            QMessageBox.warning(self, "FFmpeg not found", "Install FFmpeg before processing files.")
            return

        options = self.options_panel.selected_options()
        has_file_silence_ranges = any(self.silence_ranges_by_path.get(record.path.resolve()) for record in self.records)
        try:
            options.validate(has_file_silence_ranges=has_file_silence_ranges)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid options", str(exc))
            return
        if not self._validate_options_for_audio_records(options):
            return
        if not self._validate_time_ranges_for_records(options):
            return

        records = self.records
        if options.silence_section and not options.has_silence_times and not options.any_selected_excluding_silence:
            records = [record for record in self.records if self.silence_ranges_by_path.get(record.path.resolve())]
            if not records:
                QMessageBox.warning(self, "No silence ranges", "Add at least one waveform silence range before processing.")
                return

        self.log.clear()
        self.progress.setValue(0)
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status.showMessage("Processing...")

        self.worker_thread = QThread(self)
        self.worker = BatchProcessor(records, options, self.runner, self.silence_ranges_by_path)
        self.worker.moveToThread(self.worker_thread)

        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_message.connect(self.append_log)
        self.worker.progress_changed.connect(self.progress.setValue)
        self.worker.status_changed.connect(self.status.showMessage)
        self.worker.finished.connect(self.processing_finished)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    @Slot()
    def cancel_processing(self) -> None:
        if self.worker:
            self.worker.cancel()
            self.append_log("Cancellation requested. Current FFmpeg process will be stopped.")

    @Slot(str)
    def append_log(self, message: str) -> None:
        self.log.appendPlainText(message)

    @Slot(int, int)
    def processing_finished(self, completed: int, failed: int) -> None:
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.worker = None
        self.worker_thread = None
        self.status.showMessage(f"Done. Completed: {completed}. Failed: {failed}.")
        QMessageBox.information(self, "Processing complete", f"Completed: {completed}\nFailed: {failed}")

    def selected_record(self) -> FileRecord | None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "No file selected", "Select one recording in the file list first.")
            return None
        if len(rows) > 1:
            QMessageBox.information(self, "Choose one file", "Select one recording at a time for waveform editing.")
            return None
        return self.records[rows[0]]

    def selected_video_record(self) -> FileRecord | None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if rows and is_video_file(self.records[rows[0]].path):
            return self.records[rows[0]]

        for record in self.records:
            if is_video_file(record.path):
                return record

        QMessageBox.information(self, "No video file", "Add a video file before using detailed editing.")
        return None

    def _silence_label(self, path: Path) -> str:
        ranges = self.silence_ranges_by_path.get(path.resolve(), [])
        if not ranges:
            return ""
        total = sum(end - start for start, end in ranges)
        count_label = "range" if len(ranges) == 1 else "ranges"
        return f"{len(ranges)} {count_label}, {format_seconds(total)}"

    def _validate_options_for_audio_records(self, options) -> bool:
        audio_records = [record for record in self.records if is_audio_file(record.path)]
        if not audio_records:
            return True
        if options.has_video_operation:
            QMessageBox.warning(
                self,
                "Video-only options selected",
                "Cartoon, pixelation, blur, silhouette, black-and-white, and resize options can only be used with video files.",
            )
            return False
        if options.remove_audio:
            QMessageBox.warning(self, "Audio-only files selected", "Remove audio cannot be used on audio-only files.")
            return False
        return True

    def _validate_time_ranges_for_records(self, options) -> bool:
        ranges: list[tuple[str, int, int]] = []
        if options.extract_section:
            ranges.append(
                (
                    "Extract section",
                    parse_time_to_seconds(options.start_time, "Start time"),
                    parse_time_to_seconds(options.end_time, "End time"),
                )
            )
        if options.silence_section and options.has_silence_times:
            ranges.append(
                (
                    "Silence section",
                    parse_time_to_seconds(options.silence_start_time, "Silence start time"),
                    parse_time_to_seconds(options.silence_end_time, "Silence end time"),
                )
            )

        for record in self.records:
            if record.duration_seconds is None:
                continue
            for label, start_seconds, end_seconds in ranges:
                if start_seconds >= record.duration_seconds:
                    QMessageBox.warning(
                        self,
                        "Time range outside file",
                        f"{label} starts after the end of {record.path.name}.\n\n"
                        f"File duration: {record.duration_label}\n"
                        f"Selected start: {format_seconds(start_seconds)}",
                    )
                    return False
                if end_seconds > record.duration_seconds:
                    QMessageBox.warning(
                        self,
                        "Time range outside file",
                        f"{label} ends after the end of {record.path.name}.\n\n"
                        f"File duration: {record.duration_label}\n"
                        f"Selected end: {format_seconds(end_seconds)}",
                    )
                    return False
        return True
