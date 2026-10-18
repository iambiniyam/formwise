"""Read a batch audit log without exposing profile values."""

from __future__ import annotations

import json
from pathlib import Path


def load_audit(path: Path | str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("tool") != "formwise":
        raise TypeError("not a formwise audit file")
    files = payload.get("files")
    if not isinstance(files, list):
        raise TypeError("audit file has no files list")
    return payload


def totals(payload: dict[str, object]) -> dict[str, int]:
    files = payload.get("files", [])
    return {
        "files": len(files),
        "errors": sum(1 for item in files if item.get("error")),
        "fields": sum(int(item.get("fields") or 0) for item in files),
        "filled": sum(int(item.get("filled") or 0) for item in files),
    }
