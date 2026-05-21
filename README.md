# QuickFixEditing

QuickFixEditing is a local graphical app for batch video editing and anonymisation with FFmpeg.

It is designed for non-technical users: drag in videos or folders, tick the operations you want, and press **Start Processing**. The app builds and runs FFmpeg commands locally. It does not use Ollama or any online AI service.

## Features

- Drag-and-drop video files or folders.
- Batch process `.mp4`, `.mov`, `.mkv`, and `.avi` files.
- Extract a section using `mm:ss` or `hh:mm:ss` start/end fields.
- Extract audio only to MP3.
- Cartoon and detailed cartoon line-detection outputs, plus pixelated, blurred, silhouette, black-and-white, and resized outputs.
- Audio removal or TV-style voice anonymisation.
- Live FFmpeg command log, progress bar, completed count, failed count, and cancel button.
- Presets for common social-science research workflows.

## Output Rules

The app never overwrites original files.

All outputs are saved into a subfolder inside the input file's parent folder:

```text
QuickFixEditing files
```

If a filename already exists, the app adds a number instead of overwriting it.

## Install And Run

### Windows

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\agent-bootstrap.ps1 -Yes
.\Run QuickFixEditing Windows.cmd
```

### Linux/macOS

```sh
chmod +x ./agent-bootstrap.sh "./Run QuickFixEditing Linux.sh" "./Run QuickFixEditing macOS.command"
./agent-bootstrap.sh --yes
./"Run QuickFixEditing Linux.sh"
```

On macOS, after `chmod +x`, you can also double-click:

```text
Run QuickFixEditing macOS.command
```

## Shared QuickFix Dependencies

Setup creates and reuses one sibling dependency folder next to the app folders:

```text
QuickFixApps/
  QuickFixAppDependencies/
    .tools/
    .venvs/
    models/
  QuickFixEditing/
  QuickFixTranscription/
  QuickFixPhonemeAlignment/
```

QuickFixEditing installs its Python environment into `QuickFixAppDependencies/.venvs/QuickFixEditing` and looks for FFmpeg in `QuickFixAppDependencies/.tools/ffmpeg`. This keeps the app folder source-only and allows the other QuickFix apps to reuse the same downloaded tools.

## Manual Python Run

```sh
python3 -m venv ../QuickFixAppDependencies/.venvs/QuickFixEditing
. ../QuickFixAppDependencies/.venvs/QuickFixEditing/bin/activate
python -m pip install -r requirements.txt
python main.py
```

On Windows:

```powershell
py -3 -m venv ..\QuickFixAppDependencies\.venvs\QuickFixEditing
..\QuickFixAppDependencies\.venvs\QuickFixEditing\Scripts\python.exe -m pip install -r requirements.txt
..\QuickFixAppDependencies\.venvs\QuickFixEditing\Scripts\python.exe .\main.py
```

## Project Structure

```text
main.py
ui/
processing/
ffmpeg/
utils/
```

## Privacy Notes

- All processing runs locally through FFmpeg.
- The application does not use Ollama, cloud AI, or remote media APIs.
- If users place videos in OneDrive, Dropbox, Google Drive, or another synced folder, that sync client may upload files independently of this app.
- Anonymisation reduces identifiability but is not a formal de-identification guarantee. Review outputs before sharing.
- Cartoon uses the previous detailed line-detection approach, with a small extra nudge toward fine edges.
- Detailed cartoon uses generous line detection plus broad stylised shadow shapes to retain more facial, hand, clothing, and object structure without restoring plain source footage.
