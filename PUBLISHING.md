# Publishing To GitHub

Upload/commit these files and folders:

```text
.gitignore
AGENTS.md
LocalVideoWorkflow.ps1
README.md
Run QuickFixEditing Linux.sh
Run QuickFixEditing macOS.command
Run QuickFixEditing Windows.cmd
agent-bootstrap.ps1
agent-bootstrap.sh
ffmpeg/
local_video_workflow.py
main.py
processing/
requirements.txt
setup-linux-macos.sh
tests/
ui/
utils/
PUBLISHING.md
```

Do not upload:

```text
../QuickFixAppDependencies/
app-local .venv/
app-local .tools/
QuickFixEditing files/
```

`QuickFixAppDependencies/` is created beside the app folders on first run and should remain a local runtime cache.

## Fresh Clone Test

Linux/macOS:

```sh
chmod +x ./agent-bootstrap.sh "./Run QuickFixEditing Linux.sh"
./agent-bootstrap.sh --yes
./"Run QuickFixEditing Linux.sh"
```

Windows:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\agent-bootstrap.ps1 -Yes
.\Run QuickFixEditing Windows.cmd
```
