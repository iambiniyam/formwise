from pathlib import Path

from pypdf import PdfReader
from reportlab.pdfgen import canvas

from formwise.fields import fill_pdf, inspect_pdf, page_count, preview_pdf


def make_form(path: Path) -> Path:
    page = canvas.Canvas(str(path), pagesize=(612, 792))
    form = page.acroForm
    form.textfield(name="first_name", x=100, y=700, width=200, height=20, borderStyle="inset", forceBorder=True)
    form.textfield(name="email", x=100, y=650, width=300, height=20, borderStyle="inset", forceBorder=True)
    form.checkbox(name="agree", x=100, y=600, size=16, buttonStyle="check")
    page.showPage()
    page.save()
    return path


def test_inspect_and_fill_text_and_checkbox(tmp_path):
    source = make_form(tmp_path / "form.pdf")
    fields, pages = inspect_pdf(source)
    assert pages == 1
    assert [field.name for field in fields] == ["first_name", "email", "agree"]
    target = tmp_path / "filled.pdf"
    result = fill_pdf(source, target, {"first_name": "Jane", "email": "jane@example.com", "agree": "Yes"})
    assert set(result["filled"]) == {"first_name", "email", "agree"}
    values = PdfReader(target).get_fields()
    assert values["first_name"].get("/V") == "Jane"
    assert values["email"].get("/V") == "jane@example.com"
    assert values["agree"].get("/V") == "/Yes"
    assert page_count(target) == 1
    assert preview_pdf(target).width > 0


def test_flatten_creates_pdf(tmp_path):
    source = make_form(tmp_path / "form.pdf")
    target = tmp_path / "flat.pdf"
    fill_pdf(source, target, {"first_name": "Jane"}, flatten=True)
    assert target.exists()
    assert page_count(target) == 1
