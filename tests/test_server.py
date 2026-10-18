
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


def test_multipage_previews_and_page_placement(tmp_path, monkeypatch):
    import pypdfium2 as pdfium

    monkeypatch.setenv("FORMWISE_HOME", str(tmp_path / "home"))
    source = tmp_path / "two.pdf"
    page = canvas.Canvas(str(source), pagesize=(612, 792))
    for text in ("Page one", "Page two"):
        page.drawString(72, 720, text)
        page.showPage()
    page.save()
    client = TestClient(app)
    inspected = client.post(
        "/api/inspect",
        files={"file": ("two.pdf", source.read_bytes(), "application/pdf")},
    )
    payload = inspected.json()
    assert payload["pages"] == 2
    assert len(payload["previews"]) == 2
    filled = client.post(
        "/api/fill",
        json={
            "job": payload["job"],
            "values": {},
            "overlay": [{"page": 1, "x": 0.2, "y": 0.3, "text": "Second page value"}],
        },
    )
    assert filled.status_code == 200
    target = tmp_path / "filled.pdf"
    target.write_bytes(client.get(filled.json()["download"]).content)
    text = pdfium.PdfDocument(str(target))[1].get_textpage().get_text_range()
    assert "Second page value" in text


def test_xfa_fill_is_rejected(tmp_path, monkeypatch):
    from pypdf import PdfWriter
    from pypdf.generic import ArrayObject, DictionaryObject, NameObject

    monkeypatch.setenv("FORMWISE_HOME", str(tmp_path / "home"))
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer._root_object[NameObject("/AcroForm")] = DictionaryObject(
        {
            NameObject("/Fields"): ArrayObject([]),
            NameObject("/XFA"): ArrayObject([]),
        }
    )
    source = tmp_path / "xfa.pdf"
    with source.open("wb") as handle:
        writer.write(handle)
    client = TestClient(app)
    inspected = client.post(
        "/api/inspect",
        files={"file": ("xfa.pdf", source.read_bytes(), "application/pdf")},
    )
    assert inspected.status_code == 200
    payload = inspected.json()
    assert payload["xfa"] is True
    filled = client.post("/api/fill", json={"job": payload["job"], "values": {}})
    assert filled.status_code == 400
    assert "XFA" in filled.json()["detail"]
