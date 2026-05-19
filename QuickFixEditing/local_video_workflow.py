"""Compatibility entry point.

The previous prototype used this filename. The active application is now the
checkbox-based PySide6 workflow in main.py.
"""

from main import main


if __name__ == "__main__":
    raise SystemExit(main())
