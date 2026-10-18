import json
from pathlib import Path

from reportlab.pdfgen import canvas

from formwise.batch import fill_folder


def make_form(path: Path, label: str) -> Path:
    page = canvas.Canvas(str(path), pagesize=(612, 792))
    page.drawString(72, 720, label)
    form = page.acroForm
    form.textfield(name="first_name", x=100, y=650, width=200, height=20, borderStyle="inset", forceBorder=True)
    form.textfield(name="email", x=100, y=600, width=250, height=20, borderStyle="inset", forceBorder=True)
    page.showPage()
    page.save()
    return path


def test_batch_fills_each_pdf_and_writes_safe_audit(tmp_path):
    source = tmp_path / "forms"
    source.mkdir()
    make_form(source / "one.pdf", "One")
    make_form(source / "two.pdf", "Two")
    result = fill_folder(source, tmp_path / "out", {"first_name": "Jane", "email": "jane@example.com"})
    anchor = Path(result["audit"])
    assert len(result["files"]) == 2
    assert (tmp_path / "out" / "one.pdf").exists()
    assert (tmp_path / "out" / "two.pdf").exists()
    assert anchor.stat().st_mode & 0o777 == 0o600
    audit = json.loads(anchor.read_text())
    assert audit["tool"] == "formwise"
    assert len(audit["files"]) == 2
    assert "Jane" not in anchor.read_text()
    assert "jane@example.com" not in anchor.read_text()
    assert all(item["filled"] == 2 for item in audit["files"])
