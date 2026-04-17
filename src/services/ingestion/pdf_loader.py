from google.genai import types


def pdf_to_parts(data: bytes) -> list[types.Part]:
    """Gemini accepts PDFs natively via inline_data; wrap bytes as a single Part."""
    return [types.Part.from_bytes(data=data, mime_type="application/pdf")]
