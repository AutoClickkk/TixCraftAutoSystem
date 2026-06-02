"""GUI entry point. Run `python gui.py` to launch the desktop UI."""
from __future__ import annotations
import sys

from src.ui.app import run


if __name__ == "__main__":
    sys.exit(run())
