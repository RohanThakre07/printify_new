"""Stable local launcher for the FastAPI backend."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parent
BACKEND_MAIN = ROOT / "backend" / "app" / "main.py"
TARGET = "backend.app.main:app"


def progress(percent: int, message: str) -> None:
    print(f"[{percent:>3}%] {message}")


def validate_layout() -> None:
    progress(10, "Checking required project files...")
    if not BACKEND_MAIN.exists():
        raise SystemExit(
            "Missing backend/app/main.py in this folder. "
            "Your local copy is stale or incomplete. "
            "Repair by copying the full 'backend' folder from a fresh project copy into C:\\printify-automation."
        )


def validate_imports() -> None:
    progress(55, "Validating imports...")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        importlib.import_module("backend.app.main")
    except ModuleNotFoundError as exc:
        missing = exc.name or "<unknown>"
        raise SystemExit(
            f"Missing dependency: {missing}. Install with:\n"
            f"  .\\.venv\\Scripts\\python.exe -m pip install {missing}"
        ) from exc


if __name__ == "__main__":
    progress(0, f"Starting from {ROOT}")
    os.chdir(ROOT)
    validate_layout()
    validate_imports()
    progress(85, "Starting API on http://127.0.0.1:8000")
    progress(100, "Startup checks complete.")
    uvicorn.run(TARGET, host="127.0.0.1", port=8000, reload=False)
