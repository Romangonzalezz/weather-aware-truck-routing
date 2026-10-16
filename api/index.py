"""Vercel entry point: serves the Django API as a WSGI function."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from config.wsgi import application as app  # noqa: E402  (needs the path above)
