"""Local paths."""

from __future__ import annotations

import os
from pathlib import Path


def app_dir() -> Path:
    path = Path(os.getenv("FORMWISE_HOME", str(Path.home() / ".formwise")))
    path.mkdir(parents=True, exist_ok=True)
    return path


def profile_path() -> Path:
    return Path(os.getenv("FORMWISE_PROFILE", str(app_dir() / "profile.json")))


def output_root() -> Path:
    path = app_dir() / "out"
    path.mkdir(parents=True, exist_ok=True)
    return path
