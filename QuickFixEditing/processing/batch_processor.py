"""Sequential batch processing worker."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from ffmpeg.ffmpeg_runner import FFmpegRunner
from processing.command_builder import ProcessingOptions, build_command, command_to_text
from utils.file_utils import FileRecord


class BatchProcessor(QObject):
    """Runs FFmpeg commands sequentially on a worker thread."""

    log_message = Signal(str)
    progress_changed = Signal(int)
    status_changed = Signal(str)
    finished = Signal(int, int)

    def __init__(self, records: list[FileRecord], options: ProcessingOptions, runner: FFmpegRunner) -> None:
        super().__init__()
        self.records = records
        self.options = options
        self.runner = runner
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
        self.runner.terminate()

    def cancelled(self) -> bool:
        return self._cancelled

    @Slot()
    def run(self) -> None:
        completed = 0
        failed = 0
        total = len(self.records)

        for index, record in enumerate(self.records, start=1):
            if self._cancelled:
                self.log_message.emit("Processing cancelled.")
                break

            self.status_changed.emit(f"Processing {index} of {total}: {record.path.name}")
            self.log_message.emit("")
            self.log_message.emit(f"Processing: {record.path}")

            try:
                if not self.runner.ffmpeg_path:
                    raise RuntimeError("FFmpeg was not found.")
                command, output_path = build_command(self.runner.ffmpeg_path, record.path, self.options)
                self.log_message.emit(command_to_text(command))
                return_code = self.runner.run(command, self.log_message.emit, self.cancelled)
                if return_code == -1:
                    self.log_message.emit("Stopped by user.")
                    break
                if return_code != 0:
                    raise RuntimeError(f"FFmpeg exited with code {return_code}.")
                completed += 1
                self.log_message.emit(f"Created: {output_path}")
            except Exception as exc:
                failed += 1
                self.log_message.emit(f"Failed: {exc}")

            self.progress_changed.emit(int((index / total) * 100))

        if total == 0:
            self.progress_changed.emit(0)
        elif not self._cancelled:
            self.progress_changed.emit(100)

        self.finished.emit(completed, failed)
