"""Heuristic field proposals for scanned PDF pages."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .fields import preview_pdf


class DetectionUnavailable(RuntimeError):
    """Raised when the optional OCR engine is missing."""


LABEL_WORDS = {
    "name", "first name", "last name", "full name", "email", "e-mail", "phone",
    "telephone", "mobile", "address", "street", "city", "state", "province",
    "zip", "zip code", "postal code", "country", "date", "date of birth", "dob",
    "signature", "company", "title", "position", "occupation", "employer",
    "invoice", "reference", "account", "amount", "total", "total amount",
}
UNDERSCORE = re.compile(r"[_\-]{3,}")


@dataclass(frozen=True, slots=True)
class Candidate:
    label: str
    x: float
    y: float
    page: int = 0

    def as_dict(self) -> dict[str, object]:
        return {"label": self.label, "x": round(self.x, 4), "y": round(self.y, 4), "page": self.page}


def _normalize_label(text: str) -> str | None:
    value = " ".join(text.lower().replace("_", " ").split()).strip(" :.-")
    if value in LABEL_WORDS:
        return value.title()
    return None


def _candidate(box, text: str, width: int, height: int, page: int = 0) -> Candidate | None:
    cleaned = " ".join(text.split())
    label = None
    if ":" in cleaned:
        head = cleaned.split(":", 1)[0]
        label = _normalize_label(head)
    if label is None:
        label = _normalize_label(cleaned)
    if label is None:
        return None
    xs = [point[0] for point in box]
    ys = [point[1] for point in box]
    x = (max(xs) + max(8, width * 0.01)) / width
    y = ((min(ys) + max(ys)) / 2) / height
    if x > 0.88:
        x = 0.05
        y = min(0.98, (max(ys) + height * 0.02) / height)
    return Candidate(label, max(0.02, min(0.95, x)), max(0.02, min(0.95, y)), page)


def candidates_from_lines(lines, width: int, height: int, page: int = 0) -> list[Candidate]:
    """Convert OCR lines (box, text, score) into unique field proposals."""
    output: list[Candidate] = []
    seen: set[tuple[str, int]] = set()
    for box, text, _score in lines:
        candidate = _candidate(box, str(text), width, height, page)
        if candidate is None:
            continue
        key = (candidate.label.lower(), round(candidate.y * 20))
        if key in seen:
            continue
        seen.add(key)
        output.append(candidate)
    return output[:30]


def detect_overlay_fields(source: Path | str, page: int = 0) -> list[Candidate]:
    try:
        import numpy as np
        from rapidocr_onnxruntime import RapidOCR
    except ImportError as exc:
        raise DetectionUnavailable(
            "OCR is not installed. Install with: uv pip install 'formwise[ocr]'"
        ) from exc
    image = preview_pdf(source, page=page, scale=2.0).convert("RGB")
    array = np.asarray(image)[:, :, ::-1]
    result, _elapsed = RapidOCR()(array)
    return candidates_from_lines(result or [], image.width, image.height, page=page)
