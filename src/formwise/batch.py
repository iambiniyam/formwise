"""Batch fill a folder of PDFs and write a privacy-safe audit log."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .fields import fill_pdf, inspect_pdf
from .profile import value_for_field


def fill_folder(
    source_dir: Path | str,
    output_dir: Path | str,
    profile: dict[str, str],
    flatten: bool = False,
) -> dict[str, object]:
    source_dir = Path(source_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, object]] = []
    for source in sorted(source_dir.glob("*.pdf")):
        target = output_dir / source.name
        record: dict[str, object] = {"input": source.name, "output": target.name}
        try:
            items, pages = inspect_pdf(source)
            values = {item.name: value_for_field(item.name, profile) for item in items}
            result = fill_pdf(source, target, values, flatten=flatten)
            record.update(
                {
                    "pages": pages,
                    "fields": len(items),
                    "filled": len(result["filled"]),
                    "blank": [item.name for item in items if not values.get(item.name)],
                }
            )
        except Exception as exc:  # noqa: BLE001 - keep the batch going, report in audit
            record["error"] = str(exc)[:300]
        records.append(record)
    audit = {
        "tool": "formwise",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(source_dir),
        "files": records,
        "profile_keys": sorted(profile),
    }
    audit_path = output_dir / "audit.json"
    audit_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    audit_path.chmod(0o600)
    return {"audit": str(audit_path), "files": records}
