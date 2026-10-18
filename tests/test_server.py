
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from formwise.server import app


def test_inspect_flags_scanned_pdf(tmp_path, monkeypatch):
    monkeypatch.setenv("FORMWISE_HOME", str(tmp_path / "home"))
    source = tmp_path / "scan.pdf"
    page = canvas.Canvas(str(source), pagesize=(612, 792))
    page.drawString(72, 720, "No fields here")
    page.showPage()
    page.save()
    client = TestClient(app)
    response = client.post(
        "/api/inspect",
        files={"file": ("scan.pdf", source.read_bytes(), "application/pdf")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["scanned"] is True
    assert payload["fields"] == []


def test_scanned_overlay_fill(tmp_path, monkeypatch):
    import pypdfium2 as pdfium

    monkeypatch.setenv("FORMWISE_HOME", str(tmp_path / "home"))
    source = tmp_path / "scan.pdf"
    page = canvas.Canvas(str(source), pagesize=(612, 792))
    page.drawString(72, 720, "Scanned form")
    page.showPage()
    page.save()
    client = TestClient(app)
    inspected = client.post(
        "/api/inspect",
        files={"file": ("scan.pdf", source.read_bytes(), "application/pdf")},
    )
    job = inspected.json()["job"]
    filled = client.post(
        "/api/fill",
        json={
            "job": job,
            "values": {},
            "overlay": [{"page": 0, "x": 0.2, "y": 0.3, "text": "Jane Doe"}],
            "flatten": False,
        },
    )
    assert filled.status_code == 200
    payload = filled.json()
    assert payload["stamped"] is True
    assert payload["filled"] == ["Jane Doe"]
    target = tmp_path / "filled.pdf"
    target.write_bytes(client.get(payload["download"]).content)
    assert "Jane Doe" in pdfium.PdfDocument(str(target))[0].get_textpage().get_text_range()
