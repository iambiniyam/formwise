from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject

from formwise.fields import pdf_flags


def make_pdf(path: Path, xfa: bool = False, signature: bool = False) -> Path:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    fields = []
    if signature:
        field = writer._add_object(
            DictionaryObject(
                {NameObject("/T"): TextStringObject("signature"), NameObject("/FT"): NameObject("/Sig")}
            )
        )
        fields.append(field)
    acro = DictionaryObject({NameObject("/Fields"): ArrayObject(fields)})
    if xfa:
        acro[NameObject("/XFA")] = ArrayObject([])
    writer._root_object[NameObject("/AcroForm")] = acro
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_flags_detect_xfa_and_signature(tmp_path):
    assert pdf_flags(make_pdf(tmp_path / "plain.pdf")) == {"xfa": False, "signatures": []}
    assert pdf_flags(make_pdf(tmp_path / "xfa.pdf", xfa=True))["xfa"] is True
    assert pdf_flags(make_pdf(tmp_path / "sig.pdf", signature=True))["signatures"] == ["signature"]
