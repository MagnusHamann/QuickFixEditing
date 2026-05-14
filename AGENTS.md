# Agent Setup Guide

This repository contains a local-only FFmpeg video editing and anonymisation app.

The current version does **not** use Ollama. Do not install Ollama for this project.

## Security Rules

- Do not upload user media.
- Do not send media to remote APIs.
- Do not overwrite original files.
- Keep generated outputs inside `QuickFixEditing files`.
- Do not commit `.venv/`, `.tools/`, generated media, logs, or caches.

## Fresh Setup

### Linux/macOS

```sh
chmod +x ./agent-bootstrap.sh "./Run QuickFixEditing Linux.sh" "./Run QuickFixEditing macOS.command"
./agent-bootstrap.sh --yes
```

Run:

```sh
./"Run QuickFixEditing Linux.sh"
```

### Windows

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\agent-bootstrap.ps1 -Yes
```

Run:

```powershell
.\Run QuickFixEditing Windows.cmd
```

## Development Notes

- GUI framework: PySide6.
- FFmpeg is called through Python subprocesses.
- Main entry point: `main.py`.
- Command construction lives in `processing/command_builder.py`.
- FFmpeg filters live in `ffmpeg/filters.py`.
- File discovery and safe output paths live in `utils/file_utils.py`.
- Validation lives in `utils/validation.py`.

## Expected Fresh-Clone Behaviour

After bootstrap, the app should launch with a drag-and-drop GUI. Users can drop files/folders, select checkbox operations, and start batch processing. Outputs must be written to `QuickFixEditing files` next to each input file.
