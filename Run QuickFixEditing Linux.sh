#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
DEPENDENCY_ROOT="$(dirname "$(pwd)")/QuickFixAppDependencies"
VENV_PYTHON="$DEPENDENCY_ROOT/.venvs/QuickFixEditing/bin/python"

if [ ! -x "$VENV_PYTHON" ]; then
    ./agent-bootstrap.sh --yes || {
        echo "Setup did not complete. Run ./agent-bootstrap.sh manually to see details."
        exit 1
    }
fi

if [ -x "$VENV_PYTHON" ]; then
    exec "$VENV_PYTHON" ./main.py "$@"
fi

if command -v python3 >/dev/null 2>&1; then
    exec python3 ./main.py "$@"
fi

echo "python3 was not found."
echo "Run ./agent-bootstrap.sh first, then run this again."
exit 1
