
import pypdfium2 as pdfium
from reportlab.pdfgen import canvas

from formwise.fields import stamp_pdf


def test_stamp_scanned_pdf(tmp_path):
    source = tmp_path / "scan.pdf"
    page = canvas.Canvas(str(source), pagesize=(612, 792))
    page.drawString(72, 720, "Scanned form")
    page.showPage()
    page.save()
    target = tmp_path / "filled.pdf"
    result = stamp_pdf(source, target, [{"page": 0, "text": "Jane Doe", "x": 0.2, "y": 0.3}])
    assert result["stamped"]
    text = pdfium.PdfDocument(str(target))[0].get_textpage().get_text_range()
    assert "Jane Doe" in text
