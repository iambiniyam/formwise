
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
