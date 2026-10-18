"""Generate a small fillable PDF for examples and tests."""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfgen import canvas


def make_form(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    page = canvas.Canvas(str(path), pagesize=(612, 792))
    page.setFont("Helvetica-Bold", 18)
    page.drawString(60, 730, "VOLUNTEER APPLICATION")
    page.setFont("Helvetica", 11)
    page.drawString(60, 705, "All fields are saved on this device.")

    form = page.acroForm
    y = 650
    for label, key in [
        ("First name", "first_name"),
        ("Last name", "last_name"),
        ("Email", "email"),
        ("Phone", "phone"),
        ("Address", "address_line1"),
        ("City", "city"),
        ("State", "state"),
        ("ZIP", "postal_code"),
        ("Country", "country"),
        ("Date of birth", "date_of_birth"),
    ]:
        page.setFont("Helvetica", 10)
        page.drawString(60, y + 6, label)
        form.textfield(
            name=key,
            x=180,
            y=y,
            width=340,
            height=20,
            borderStyle="inset",
            forceBorder=True,
            fontName="Helvetica",
            fontSize=10,
        )
        y -= 42

    page.setFont("Helvetica", 10)
    page.drawString(60, y + 6, "I agree to the terms")
    form.checkbox(name="agree", x=220, y=y, size=16, buttonStyle="check", checked=False)
    page.showPage()
    page.save()
    return path


if __name__ == "__main__":
    print(make_form(Path("examples/sample-form.pdf")))
