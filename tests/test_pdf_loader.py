from src.services.ingestion.pdf_loader import pdf_to_parts


def test_pdf_to_parts_wraps_bytes():
    data = b"%PDF-1.4 ..."
    parts = pdf_to_parts(data)
    assert len(parts) == 1
    part = parts[0]
    inline = part.inline_data
    assert inline is not None
    assert inline.mime_type == "application/pdf"
    assert inline.data == data
