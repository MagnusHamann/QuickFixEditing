# QuickFix Editing

QuickFix Editing is a local graphical app for batch video editing and anonymisation with FFmpeg.

It is designed for non-technical users: drag in videos or folders, tick the operations you want, and press **Start Processing**. The app builds and runs FFmpeg commands locally. It does not use Ollama or any online AI service.

## Features

- Drag-and-drop video files or folders.
- Batch process `.mp4`, `.mov`, `.mkv`, and `.avi` files.
- Show filename, duration, resolution, and file size.
- Extract a section using `mm:ss` or `hh:mm:ss` start/end fields.
- Extract audio only to MP3.
- Light anonymisation with a cartoon-style black-on-white line drawing.
- Very light anonymisation with a more detailed cartoon line drawing for internal review where more facial detail should remain visible.
- Medium anonymisation with pixelation.
- Strong anonymisation with blur.
- Extreme anonymisation with silhouette-style processing.
- Distort audio with a TV-style voice anonymisation effect.
- Remove audio.
- Convert to black and white.
- Resize to 480p, 720p, or 1080p.
- Live FFmpeg command log.
- Progress bar, completed count, failed count, and cancel button.
- Presets for common social-science research workflows.

## Research Presets

- **Observation sharing**: cartoon line drawing plus removed audio, useful when showing contextual movement without voices.
- **Interview review**: pixelation plus distorted audio, useful for team review where facial detail and natural voice should be withheld.
- **Fieldnote coding**: cartoon line drawing, black and white, and 720p resize, useful for coding visible action while keeping files manageable.
- **Maximum participant privacy**: silhouette mode plus distorted audio, useful for strong visual anonymisation while preserving interaction audio timing.
- **Audio for transcription**: exports MP3 audio only.

## Output Rules

The app never overwrites original files.

All outputs are saved into a subfolder inside the input file's parent folder:

```text
QuickFixEditing files
```

Example:

```text
Input:
C:/Videos/interview.mp4

Output:
C:/Videos/QuickFixEditing files/interview_blurred.mp4
```

When multiple operations are selected, suffixes are combined:

```text
interview_trimmed_blurred.mp4
interview_trimmed_blurred_muted.mp4
interview_detailedcartoon.mp4
interview_audio.mp3
```

If a filename already exists, the app adds a number instead of overwriting it.

## Install And Run

### Windows

From PowerShell in the repository folder:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\agent-bootstrap.ps1 -Yes
.\Run QuickFixEditing Windows.cmd
```

The Windows bootstrap checks for Python and FFmpeg. It uses `winget` when available and installs Python dependencies into `.venv`.

### Linux/macOS

From a terminal in the repository folder:

```sh
chmod +x ./agent-bootstrap.sh "./Run QuickFixEditing Linux.sh" "./Run QuickFixEditing macOS.command"
./agent-bootstrap.sh --yes
./"Run QuickFixEditing Linux.sh"
```

On macOS, after `chmod +x`, you can also double-click:

```text
Run QuickFixEditing macOS.command
```

## Manual Python Run

```sh
python3 -m venv .venv
. ./.venv/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe .\main.py
```

## FFmpeg Installation

The bootstrap scripts try to install FFmpeg where possible.

- Windows: `winget install -e --id Gyan.FFmpeg`
- macOS: `brew install ffmpeg`
- Debian/Ubuntu: `sudo apt-get install ffmpeg`
- Fedora: `sudo dnf install ffmpeg`
- Arch: `sudo pacman -S ffmpeg`

If automatic setup fails, install FFmpeg manually from:

```text
https://ffmpeg.org/download.html
```

## Project Structure

```text
main.py
ui/
  main_window.py
  drag_drop_widget.py
  options_panel.py
processing/
  batch_processor.py
  command_builder.py
ffmpeg/
  ffmpeg_runner.py
  filters.py
utils/
  file_utils.py
  validation.py
```

The GUI is separated from command construction and FFmpeg execution so new operations can be added safely.

## Agentic AI Setup

Agents such as Codex should read [AGENTS.md](AGENTS.md), then run:

Linux/macOS:

```sh
chmod +x ./agent-bootstrap.sh "./Run QuickFixEditing Linux.sh"
./agent-bootstrap.sh --yes
```

Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\agent-bootstrap.ps1 -Yes
```

## Privacy Notes

- All processing runs locally through FFmpeg.
- The application does not use Ollama, cloud AI, or remote media APIs.
- If users place videos in OneDrive, Dropbox, Google Drive, or another synced folder, that sync client may upload files independently of this app.
- Anonymisation reduces identifiability but is not a formal de-identification guarantee. Review outputs before sharing.
- The very light detailed cartoon mode intentionally retains more facial detail and is therefore less privacy-protective than the stronger anonymisation modes.
