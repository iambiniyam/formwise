"""Inspect and fill PDF AcroForm fields."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

TYPE_NAMES = {"/Tx": "text", "/Btn": "button", "/Ch": "choice", "/Sig": "signature"}


@dataclass(slots=True)
class FieldInfo:
    name: str
    field_type: str
    value: str
    options: list[str]
    suggested_key: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "type": self.field_type,
            "value": self.value,
            "options": self.options,
            "suggested_key": self.suggested_key,
        }


def inspect_pdf(path: Path | str) -> tuple[list[FieldInfo], int]:
    reader = PdfReader(str(path))
    fields = reader.get_fields() or {}
    output: list[FieldInfo] = []
    for name, field in fields.items():
        raw_type = str(field.get("/FT", ""))
        field_type = TYPE_NAMES.get(raw_type, raw_type.lstrip("/") or "unknown")
        options = [str(item) for item in (field.get("/Opt") or [])]
        value = field.get("/V", "")
        output.append(
            FieldInfo(
                name=str(name),
                field_type=field_type,
                value="" if value is None else str(value),
                options=options,
            )
        )
    return output, len(reader.pages)


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _widget_name(annotation) -> str:
    if "/T" in annotation:
        return str(annotation["/T"])
    parent = annotation.get("/Parent")
    if parent:
        return str(parent.get_object().get("/T", ""))
    return ""


def _set_text_appearance(annotation, value: str) -> None:
    rectangle = annotation.get("/Rect")
    if not rectangle:
        return
    x0, y0, x1, y1 = (float(item) for item in rectangle)
    width = max(1.0, x1 - x0)
    height = max(1.0, y1 - y0)
    size = min(10.0, max(6.0, height * 0.55))
    text = _escape_pdf_text(value[:80])
    content = (
        f"q\n1 1 1 rg\n0 0 {width:.2f} {height:.2f} re f\n"
        f"0.55 0.55 0.55 RG 0.6 w 0 0 {width:.2f} {height:.2f} re S\n"
        f"0 0 0 rg\nBT\n/Helv {size:.2f} Tf\n2 {height - size - 2:.2f} Td\n({text}) Tj\nET\nQ"
    )
    stream = DecodedStreamObject()
    stream.set_data(content.encode("latin-1", "replace"))
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    stream.update(
        {
            NameObject("/Type"): NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/FormType"): NumberObject(1),
            NameObject("/BBox"): ArrayObject(
                [FloatObject(0), FloatObject(0), FloatObject(width), FloatObject(height)]
            ),
            NameObject("/Resources"): DictionaryObject(
                {NameObject("/Font"): DictionaryObject({NameObject("/Helv"): font})}
            ),
        }
    )
    annotation[NameObject("/AP")] = DictionaryObject({NameObject("/N"): stream})


def fill_pdf(
    source: Path | str,
    output: Path | str,
    values: dict[str, str],
    flatten: bool = False,
) -> dict[str, object]:
    reader = PdfReader(str(source))
    writer = PdfWriter(clone_from=reader)
    filled: list[str] = []
    for page in writer.pages:
        from io import BytesIO

        from reportlab.pdfgen import canvas as rl_canvas

        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        buffer = BytesIO()
        layer = rl_canvas.Canvas(buffer, pagesize=(width, height))
        remaining = []
        for reference in page.get("/Annots", []):
            annotation = reference.get_object()
            if annotation.get("/Subtype") != "/Widget":
                remaining.append(reference)
                continue
            name = _widget_name(annotation)
            if name not in values or values[name] == "":
                continue
            value = values[name]
            rectangle = annotation.get("/Rect")
            if not rectangle:
                continue
            x0, y0, x1, y1 = (float(item) for item in rectangle)
            field_width = max(1.0, x1 - x0)
            field_height = max(1.0, y1 - y0)
            layer.setFillColorRGB(0.93, 0.95, 1.0)
            layer.setStrokeColorRGB(0.62, 0.66, 0.74)
            layer.setLineWidth(0.6)
            layer.rect(x0, y0, field_width, field_height, fill=1, stroke=1)
            if str(annotation.get("/FT", "/Tx")) == "/Btn":
                lowered = value.strip().lower()
                state = "/Yes" if lowered in {"yes", "true", "on", "1", "/yes"} else "/Off"
                annotation[NameObject("/V")] = NameObject(state)
                if state == "/Yes":
                    layer.setStrokeColorRGB(0, 0, 0)
                    layer.setLineWidth(1.6)
                    layer.line(x0 + 3, y0 + field_height * 0.5, x0 + field_width * 0.4, y0 + 3)
                    layer.line(x0 + field_width * 0.4, y0 + 3, x1 - 3, y1 - 3)
            else:
                annotation[NameObject("/V")] = TextStringObject(value)
                size = min(10.0, max(6.0, field_height * 0.55))
                text = str(value)
                layer.setFillColorRGB(0, 0, 0)
                layer.setFont("Helvetica", size)
                while text and layer.stringWidth(text, "Helvetica", size) > field_width - 5:
                    text = text[:-1]
                layer.drawString(x0 + 3, y0 + (field_height - size) / 2 + 1, text)
            filled.append(name)
        layer.save()
        buffer.seek(0)
        page.merge_page(PdfReader(buffer).pages[0])
        page[NameObject("/Annots")] = ArrayObject(remaining)

    output = Path(output)
    _write_output(writer, output, flatten)
    return {"output": str(output), "filled": sorted(set(filled))}


def _write_output(writer, output: Path, flatten: bool) -> None:
    from io import BytesIO

    if flatten:
        buffer = BytesIO()
        writer.write(buffer)
        buffer.seek(0)
        pdf = pdfium.PdfDocument(buffer.read())
        images = [
            pdf[index].render(scale=200 / 72).to_pil().convert("RGB")
            for index in range(len(pdf))
        ]
        if images:
            images[0].save(output, save_all=True, append_images=images[1:], format="PDF", resolution=200)
    else:
        with output.open("wb") as handle:
            writer.write(handle)


def stamp_pdf(
    source: Path | str,
    output: Path | str,
    overlays: list[dict[str, object]],
    flatten: bool = False,
) -> dict[str, object]:
    """Place text at normalized page coordinates for a scanned PDF."""
    from io import BytesIO

    from reportlab.pdfgen import canvas as rl_canvas

    reader = PdfReader(str(source))
    writer = PdfWriter(clone_from=reader)
    pages = list(writer.pages)
    stamped: list[dict[str, object]] = []
    for item in overlays:
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        page_index = max(0, min(len(pages) - 1, int(item.get("page") or 0)))
        page = pages[page_index]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        x = max(0.0, min(1.0, float(item.get("x") or 0.0)))
        y = max(0.0, min(1.0, float(item.get("y") or 0.0)))
        size = max(6.0, min(48.0, float(item.get("size") or 11.0)))
        buffer = BytesIO()
        layer = rl_canvas.Canvas(buffer, pagesize=(width, height))
        layer.setFillColorRGB(0, 0, 0)
        layer.setFont("Helvetica", size)
        layer.drawString(x * width, (1.0 - y) * height - size, text[:300])
        layer.save()
        buffer.seek(0)
        page.merge_page(PdfReader(buffer).pages[0])
        stamped.append({"page": page_index + 1, "text": text[:300], "x": round(x, 4), "y": round(y, 4)})
    output = Path(output)
    _write_output(writer, output, flatten)
    return {"output": str(output), "stamped": stamped}


def preview_pdf(path: Path | str, page: int = 0, scale: float = 1.5) -> Image.Image:
    pdf = pdfium.PdfDocument(str(path))
    if page < 0 or page >= len(pdf):
        raise IndexError(page)
    return pdf[page].render(scale=scale).to_pil().convert("RGB")


def page_count(path: Path | str) -> int:
    return len(pdfium.PdfDocument(str(path)))
