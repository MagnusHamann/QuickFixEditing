from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from processing.command_builder import DetailedEditSettings, ProcessingOptions, build_command, normalized_ranges, silence_filter


class SilenceCommandBuilderTests(unittest.TestCase):
    def test_silence_range_filter_uses_volume_enable(self) -> None:
        audio_filter = silence_filter([(10, 20.5)])

        self.assertIn("volume=volume=0", audio_filter)
        self.assertIn("between(t,10.000,20.500)", audio_filter)

    def test_overlapping_silence_ranges_are_merged(self) -> None:
        ranges = normalized_ranges([(12, 20), (5, 10), (9, 13), (30, 31)])

        self.assertEqual(ranges, [(5.0, 20.0), (30.0, 31.0)])

    def test_builds_silence_command_without_changing_video_duration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "interview.mp4"
            input_file.write_bytes(b"")
            options = ProcessingOptions(
                silence_section=True,
                silence_start_time="00:10",
                silence_end_time="00:20",
            )

            command, output_path = build_command("ffmpeg", input_file, options)

        self.assertEqual(output_path.name, "interview_silenced.mp4")
        self.assertIn("-af", command)
        self.assertIn("between(t,10.000,20.000)", " ".join(command))
        self.assertIn("-c:v", command)
        self.assertEqual(command[command.index("-c:v") + 1], "copy")

    def test_partial_silence_time_is_invalid(self) -> None:
        options = ProcessingOptions(silence_section=True, silence_start_time="00:10")

        with self.assertRaisesRegex(ValueError, "both a start time and an end time"):
            options.validate(has_file_silence_ranges=True)

    def test_audio_input_outputs_mp3(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "interview.wav"
            input_file.write_bytes(b"")
            options = ProcessingOptions(
                extract_section=True,
                start_time="00:01",
                end_time="00:04",
                silence_section=True,
                silence_start_time="00:02",
                silence_end_time="00:03",
            )

            command, output_path = build_command("ffmpeg", input_file, options)

        self.assertEqual(output_path.name, "interview_trimmed_silenced.mp3")
        self.assertIn("-vn", command)
        self.assertIn("libmp3lame", command)
        self.assertNotIn("-map 0:v:0", " ".join(command))

    def test_video_only_options_are_invalid_for_audio_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "interview.mp3"
            input_file.write_bytes(b"")
            options = ProcessingOptions(line_drawing=True)

            with self.assertRaisesRegex(ValueError, "only be used with video files"):
                build_command("ffmpeg", input_file, options)

    def test_detailed_edit_settings_change_video_filter_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_file = Path(temp_dir) / "interview.mp4"
            input_file.write_bytes(b"")
            options = ProcessingOptions(
                pixelation=True,
                blur=True,
                detailed_settings=DetailedEditSettings(pixel_size=12, blur_sigma=33),
            )

            command, _ = build_command("ffmpeg", input_file, options)

        command_text = " ".join(command)
        self.assertIn("scale=iw/12:ih/12", command_text)
        self.assertIn("gblur=sigma=33", command_text)


if __name__ == "__main__":
    unittest.main()
